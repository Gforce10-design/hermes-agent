import 'dart:convert';
import 'dart:io';

import 'hermes_ws_client.dart';

class HermesServiceStatus {
  const HermesServiceStatus({
    required this.service,
    required this.state,
    required this.detail,
  });

  final String service;
  final String state;
  final String detail;

  factory HermesServiceStatus.fromJson(Map<String, dynamic> json) {
    return HermesServiceStatus(
      service: '${json['service'] ?? 'Hermes Agent'}',
      state: '${json['state'] ?? 'unknown'}',
      detail: '${json['detail'] ?? ''}',
    );
  }
}

class AlphaMateStatus {
  const AlphaMateStatus({
    required this.state,
    required this.summary,
    required this.detail,
  });

  final String state;
  final String summary;
  final String detail;

  factory AlphaMateStatus.fromJson(Map<String, dynamic> json) {
    return AlphaMateStatus(
      state: '${json['state'] ?? 'placeholder'}',
      summary: '${json['summary'] ?? ''}',
      detail: '${json['detail'] ?? ''}',
    );
  }
}

class MobileApiStatus {
  const MobileApiStatus({
    required this.state,
    required this.auth,
    required this.detail,
  });

  final String state;
  final String auth;
  final String detail;

  factory MobileApiStatus.fromJson(Map<String, dynamic> json) {
    return MobileApiStatus(
      state: '${json['state'] ?? 'unknown'}',
      auth: '${json['auth'] ?? 'unknown'}',
      detail: '${json['detail'] ?? ''}',
    );
  }
}

class HermesNotification {
  const HermesNotification({
    required this.id,
    required this.severity,
    required this.title,
    required this.message,
    required this.createdAt,
  });

  final String id;
  final String severity;
  final String title;
  final String message;
  final String createdAt;

  factory HermesNotification.fromJson(Map<String, dynamic> json) {
    return HermesNotification(
      id: '${json['id'] ?? ''}',
      severity: '${json['severity'] ?? 'info'}',
      title: '${json['title'] ?? ''}',
      message: '${json['message'] ?? ''}',
      createdAt: '${json['created_at'] ?? ''}',
    );
  }
}

class MobileStatusSnapshot {
  const MobileStatusSnapshot({
    required this.generatedAt,
    required this.hermes,
    required this.mobileApi,
    required this.alphaMate,
    required this.notifications,
  });

  final String generatedAt;
  final HermesServiceStatus hermes;
  final MobileApiStatus mobileApi;
  final AlphaMateStatus alphaMate;
  final List<HermesNotification> notifications;

  factory MobileStatusSnapshot.fromJson(Map<String, dynamic> json) {
    final notificationsJson = json['notifications'];
    return MobileStatusSnapshot(
      generatedAt: '${json['generated_at'] ?? ''}',
      hermes: HermesServiceStatus.fromJson(
        (json['hermes'] as Map?)?.cast<String, dynamic>() ?? const {},
      ),
      mobileApi: MobileApiStatus.fromJson(
        (json['mobile_api'] as Map?)?.cast<String, dynamic>() ?? const {},
      ),
      alphaMate: AlphaMateStatus.fromJson(
        (json['alpha_mate'] as Map?)?.cast<String, dynamic>() ?? const {},
      ),
      notifications: notificationsJson is List
          ? notificationsJson
              .whereType<Map>()
              .map((item) => HermesNotification.fromJson(
                    item.cast<String, dynamic>(),
                  ))
              .toList(growable: false)
          : const [],
    );
  }
}

abstract interface class HermesStatusService {
  Future<MobileStatusSnapshot> fetchStatus({
    required String serverUrl,
    required String sessionToken,
    required String cloudflareAccessClientId,
    required String cloudflareAccessClientSecret,
  });
}

class HermesRestClient implements HermesStatusService {
  const HermesRestClient();

  static Uri buildStatusUri({required String serverUrl}) {
    final origin = HermesWsClient.parseServerOrigin(serverUrl);
    return origin.replace(path: '/api/mobile/status', query: null, fragment: null);
  }

  @override
  Future<MobileStatusSnapshot> fetchStatus({
    required String serverUrl,
    required String sessionToken,
    required String cloudflareAccessClientId,
    required String cloudflareAccessClientSecret,
  }) async {
    final uri = buildStatusUri(serverUrl: serverUrl);
    final accessHeaders = HermesWsClient.buildAccessHeaders(
      cloudflareAccessClientId: cloudflareAccessClientId,
      cloudflareAccessClientSecret: cloudflareAccessClientSecret,
    );
    final client = HttpClient();
    try {
      final request = await client.getUrl(uri);
      request.followRedirects = false;
      for (final entry in accessHeaders.entries) {
        request.headers.set(entry.key, entry.value);
      }
      final trimmedSessionToken = sessionToken.trim();
      if (trimmedSessionToken.isNotEmpty) {
        request.headers.set('X-Hermes-Session-Token', trimmedSessionToken);
      }
      final response = await request.close();
      final body = await response.transform(utf8.decoder).join();
      if (response.statusCode != HttpStatus.ok) {
        throw StateError(HermesWsClient.describeBootstrapFailure(
          statusCode: response.statusCode,
          location: response.headers.value(HttpHeaders.locationHeader),
        ));
      }
      final decoded = jsonDecode(body);
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException('Invalid mobile status response');
      }
      return MobileStatusSnapshot.fromJson(decoded);
    } finally {
      client.close(force: true);
    }
  }
}
