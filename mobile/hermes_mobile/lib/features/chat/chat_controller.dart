import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../services/hermes_ws_client.dart';
import 'message_model.dart';

typedef HermesTransportFactory = HermesMessageTransport Function({
  required String serverUrl,
  required String sessionToken,
});

class ChatController extends ChangeNotifier {
  ChatController({
    required this.serverUrl,
    required this.sessionToken,
    HermesTransportFactory? transportFactory,
  }) : _transportFactory = transportFactory ?? HermesWsClient.connect;

  final String serverUrl;
  final String sessionToken;
  final HermesTransportFactory _transportFactory;

  final List<HermesMessage> _messages = [];
  HermesMessageTransport? _transport;
  StreamSubscription<Map<String, dynamic>>? _subscription;
  bool _connected = false;
  bool _sending = false;
  String? _error;
  String? _sessionId;

  List<HermesMessage> get messages => List.unmodifiable(_messages);
  bool get connected => _connected;
  bool get sending => _sending;
  String? get error => _error;

  Future<void> connect() async {
    if (_connected) return;
    if (sessionToken.trim().isEmpty) {
      _error = '세션 토큰을 입력해 주세요.';
      notifyListeners();
      return;
    }
    _transport = _transportFactory(serverUrl: serverUrl, sessionToken: sessionToken);
    _subscription = _transport!.events.listen(
      _handleEvent,
      onError: (Object error) {
        _error = '연결 오류: $error';
        _connected = false;
        notifyListeners();
      },
      onDone: () {
        _connected = false;
        notifyListeners();
      },
    );
    _connected = true;
    _error = null;
    notifyListeners();
  }

  Future<void> sendPrompt(String text) async {
    final prompt = text.trim();
    if (prompt.isEmpty) return;
    await connect();
    if (!_connected || _transport == null) return;

    _messages.add(HermesMessage(role: HermesMessageRole.user, text: prompt));
    _sending = true;
    _error = null;
    notifyListeners();

    final payload = <String, dynamic>{
      'type': 'prompt.submit',
      'text': prompt,
      'client': 'flutter',
    };
    if (_sessionId != null) payload['session_id'] = _sessionId;
    _transport!.send(payload);
  }

  void _handleEvent(Map<String, dynamic> event) {
    switch (event['type']) {
      case 'message.start':
        _messages.add(const HermesMessage(role: HermesMessageRole.assistant, text: '', pending: true));
        break;
      case 'message.delta':
        _appendAssistantDelta('${event['text'] ?? ''}');
        break;
      case 'message.complete':
        _completeAssistantMessage(
          '${event['text'] ?? ''}',
          sessionId: event['session_id']?.toString(),
        );
        break;
      case 'tool.start':
        _messages.add(HermesMessage(role: HermesMessageRole.tool, text: '${event['summary'] ?? event['name'] ?? '도구 실행 중'}', pending: true));
        break;
      case 'tool.complete':
        _messages.add(HermesMessage(role: HermesMessageRole.tool, text: '${event['name'] ?? '도구'} 완료'));
        break;
      case 'approval.request':
        _messages.add(HermesMessage(role: HermesMessageRole.system, text: '${event['text'] ?? '승인이 필요합니다.'}'));
        break;
      case 'error':
        _error = '${event['message'] ?? '알 수 없는 오류'}';
        _sending = false;
        break;
      default:
        _messages.add(HermesMessage(role: HermesMessageRole.system, text: '알 수 없는 이벤트: ${event['type']}'));
    }
    notifyListeners();
  }

  void _appendAssistantDelta(String delta) {
    final index = _messages.lastIndexWhere((msg) => msg.role == HermesMessageRole.assistant && msg.pending);
    if (index == -1) {
      _messages.add(HermesMessage(role: HermesMessageRole.assistant, text: delta, pending: true));
      return;
    }
    final current = _messages[index];
    _messages[index] = current.copyWith(text: current.text + delta);
  }

  void _completeAssistantMessage(String text, {String? sessionId}) {
    if (sessionId != null && sessionId.isNotEmpty) _sessionId = sessionId;
    final index = _messages.lastIndexWhere((msg) => msg.role == HermesMessageRole.assistant && msg.pending);
    if (index == -1) {
      _messages.add(HermesMessage(role: HermesMessageRole.assistant, text: text));
    } else {
      _messages[index] = _messages[index].copyWith(text: text, pending: false);
    }
    _sending = false;
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _transport?.close();
    super.dispose();
  }
}
