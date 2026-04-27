import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

abstract interface class HermesMessageTransport {
  Stream<Map<String, dynamic>> get events;
  void send(Map<String, dynamic> payload);
  Future<void> close();
}

class HermesWsClient implements HermesMessageTransport {
  HermesWsClient._(this._channel)
      : events = _channel.stream.map((event) {
          final decoded = jsonDecode(event as String);
          if (decoded is Map<String, dynamic>) return decoded;
          return <String, dynamic>{'type': 'error', 'message': 'Invalid server event'};
        });

  factory HermesWsClient.connect({
    required String serverUrl,
    required String sessionToken,
  }) {
    final httpUri = Uri.parse(serverUrl);
    final scheme = httpUri.scheme == 'https' ? 'wss' : 'ws';
    final path = httpUri.path.endsWith('/')
        ? '${httpUri.path}api/mobile/ws'
        : '${httpUri.path}/api/mobile/ws';
    final wsUri = httpUri.replace(
      scheme: scheme,
      path: path,
      queryParameters: {'token': sessionToken},
    );
    return HermesWsClient._(WebSocketChannel.connect(wsUri));
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
