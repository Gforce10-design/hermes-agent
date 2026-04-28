import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

abstract interface class HermesMessageTransport {
  Stream<Map<String, dynamic>> get events;
  void send(Map<String, dynamic> payload);
  Future<void> close();
}

class AccessConnectionDiagnostics {
  const AccessConnectionDiagnostics({
    required this.bootstrapUri,
    required this.clientIdPresent,
    required this.clientSecretPresent,
    required this.clientIdLength,
    required this.clientSecretLength,
    required this.headersPresent,
  });

  final Uri bootstrapUri;
  final bool clientIdPresent;
  final bool clientSecretPresent;
  final int clientIdLength;
  final int clientSecretLength;
  final bool headersPresent;

  String get safeSummary {
    final headerState = headersPresent ? 'Access 헤더 생성됨' : 'Access 헤더 미생성';
    return '$headerState · Client ID ${clientIdPresent ? '입력됨' : '비어 있음'}($clientIdLength자) · Secret ${clientSecretPresent ? '입력됨' : '비어 있음'}($clientSecretLength자) · 요청 $bootstrapUri';
  }
}

class HermesWsClient implements HermesMessageTransport {
  HermesWsClient._(this._channel)
      : events = _channel.stream.map((event) {
          final decoded = jsonDecode(event as String);
          if (decoded is Map<String, dynamic>) return decoded;
          return <String, dynamic>{
            'type': 'error',
            'message': 'Invalid server event'
          };
        });

  static Future<HermesWsClient> connect({
    required String serverUrl,
    required String sessionToken,
    String cloudflareAccessClientId = '',
    String cloudflareAccessClientSecret = '',
  }) async {
    final accessHeaders = buildAccessHeaders(
      cloudflareAccessClientId: cloudflareAccessClientId,
      cloudflareAccessClientSecret: cloudflareAccessClientSecret,
    );
    String? mobileWsUrl;
    if (sessionToken.trim().isEmpty) {
      mobileWsUrl = await fetchMobileWsUrl(
        serverUrl: serverUrl,
        accessHeaders: accessHeaders,
      );
    }
    return HermesWsClient._(IOWebSocketChannel.connect(
      buildMobileWsUri(
        serverUrl: serverUrl,
        sessionToken: sessionToken,
        mobileWsUrl: mobileWsUrl,
      ),
      headers: accessHeaders.isEmpty ? null : accessHeaders,
    ));
  }

  static Map<String, String> buildAccessHeaders({
    required String cloudflareAccessClientId,
    required String cloudflareAccessClientSecret,
  }) {
    final clientId = _sanitizeAccessTokenPart(cloudflareAccessClientId);
    final clientSecret = _sanitizeAccessTokenPart(cloudflareAccessClientSecret);
    if (clientId.isEmpty || clientSecret.isEmpty) return const {};
    return {
      'CF-Access-Client-Id': clientId,
      'CF-Access-Client-Secret': clientSecret,
    };
  }

  static AccessConnectionDiagnostics buildAccessDiagnostics({
    required String serverUrl,
    required String cloudflareAccessClientId,
    required String cloudflareAccessClientSecret,
  }) {
    final clientId = _sanitizeAccessTokenPart(cloudflareAccessClientId);
    final clientSecret = _sanitizeAccessTokenPart(cloudflareAccessClientSecret);
    return AccessConnectionDiagnostics(
      bootstrapUri: buildBootstrapUri(serverUrl: serverUrl),
      clientIdPresent: clientId.isNotEmpty,
      clientSecretPresent: clientSecret.isNotEmpty,
      clientIdLength: clientId.length,
      clientSecretLength: clientSecret.length,
      headersPresent: clientId.isNotEmpty && clientSecret.isNotEmpty,
    );
  }

  static String _sanitizeAccessTokenPart(String value) {
    return value.replaceAll(RegExp(r'[\s\u200B-\u200D\uFEFF]+'), '');
  }

  static Uri buildBootstrapUri({required String serverUrl}) {
    final baseUri = _originUri(serverUrl);
    return baseUri.replace(
        path: '/api/mobile/bootstrap', query: null, fragment: null);
  }

  static Uri buildMobileWsUri({
    required String serverUrl,
    required String sessionToken,
    String? mobileWsUrl,
  }) {
    final baseUri = _originUri(serverUrl);
    final scheme = baseUri.scheme == 'https' ? 'wss' : 'ws';
    final wsBaseUri = baseUri.replace(scheme: scheme);

    if (mobileWsUrl != null && mobileWsUrl.trim().isNotEmpty) {
      final parsed = Uri.parse(mobileWsUrl);
      return parsed.hasScheme ? parsed : wsBaseUri.resolveUri(parsed);
    }

    return wsBaseUri.replace(
      path: '/api/mobile/ws',
      queryParameters:
          sessionToken.trim().isEmpty ? null : {'token': sessionToken.trim()},
    );
  }

  static String describeBootstrapFailure({
    required int statusCode,
    String? location,
  }) {
    final redirect = location ?? '';
    final redirectHost = Uri.tryParse(redirect)?.host;
    final hostText = redirectHost == null || redirectHost.isEmpty
        ? ''
        : ' redirect host: $redirectHost';
    if ((statusCode == HttpStatus.found ||
            statusCode == HttpStatus.movedPermanently ||
            statusCode == HttpStatus.temporaryRedirect ||
            statusCode == HttpStatus.permanentRedirect) &&
        redirect.contains('cloudflareaccess.com')) {
      return 'Cloudflare Access 로그인으로 이동했습니다. Service Token 값 또는 Access 앱 정책 허용을 확인하세요.$hostText ($statusCode)';
    }
    if (statusCode == HttpStatus.forbidden) {
      return 'Cloudflare Access가 요청을 거부했습니다. Service Token이 해당 앱 정책에 허용되어 있는지 확인하세요. (403)';
    }
    if (statusCode == HttpStatus.unauthorized) {
      return 'Hermes 인증이 거부되었습니다. 서버 URL 또는 세션 설정을 확인하세요. (401)';
    }
    return '모바일 자동 연결 정보를 가져오지 못했습니다. ($statusCode)';
  }

  static Future<String> fetchMobileWsUrl({
    required String serverUrl,
    Map<String, String> accessHeaders = const {},
  }) async {
    final uri = buildBootstrapUri(serverUrl: serverUrl);
    final client = HttpClient();
    try {
      final request = await client.getUrl(uri);
      request.followRedirects = false;
      for (final entry in accessHeaders.entries) {
        request.headers.set(entry.key, entry.value);
      }
      final response = await request.close();
      final body = await utf8.decoder.bind(response).join();
      if (response.statusCode != HttpStatus.ok) {
        throw StateError(describeBootstrapFailure(
          statusCode: response.statusCode,
          location: response.headers.value(HttpHeaders.locationHeader),
        ));
      }
      final decoded = jsonDecode(body);
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException('Invalid mobile bootstrap response');
      }
      final wsUrl = decoded['mobile_ws_url']?.toString() ?? '';
      if (wsUrl.isEmpty) {
        throw const FormatException('Missing mobile_ws_url');
      }
      return wsUrl;
    } finally {
      client.close(force: true);
    }
  }

  static Uri parseServerOrigin(String serverUrl) => _originUri(serverUrl);

  static Uri _originUri(String serverUrl) {
    final parsed = Uri.parse(serverUrl.trim());
    return parsed.replace(path: '', query: null, fragment: null);
  }

  final WebSocketChannel _channel;

  @override
  final Stream<Map<String, dynamic>> events;

  @override
  void send(Map<String, dynamic> payload) {
    _channel.sink.add(jsonEncode(payload));
  }

  @override
  Future<void> close() async {
    await _channel.sink.close();
  }
}
