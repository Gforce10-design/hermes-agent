import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../services/hermes_ws_client.dart';
import 'message_model.dart';

typedef HermesTransportFactory = FutureOr<HermesMessageTransport> Function({
  required String serverUrl,
  required String sessionToken,
  required String cloudflareAccessClientId,
  required String cloudflareAccessClientSecret,
});

class ChatController extends ChangeNotifier {
  static const _historyMessagesKey = 'chat.history.messages';
  static const _historySessionKey = 'chat.history.sessionId';

  ChatController({
    required this.serverUrl,
    required this.sessionToken,
    this.cloudflareAccessClientId = '',
    this.cloudflareAccessClientSecret = '',
    HermesTransportFactory? transportFactory,
  }) : _transportFactory = transportFactory ?? HermesWsClient.connect;

  final String serverUrl;
  final String sessionToken;
  final String cloudflareAccessClientId;
  final String cloudflareAccessClientSecret;
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

  Future<void> restoreHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final rawMessages = prefs.getString(_historyMessagesKey);
    _sessionId = prefs.getString(_historySessionKey);
    if (rawMessages == null || rawMessages.isEmpty) return;
    final decoded = jsonDecode(rawMessages);
    if (decoded is! List) return;
    _messages
      ..clear()
      ..addAll(decoded
          .whereType<Map>()
          .map(
              (item) => HermesMessage.fromJson(Map<String, dynamic>.from(item)))
          .where((message) => !message.pending));
    notifyListeners();
  }

  Future<void> clearHistory() async {
    _messages.clear();
    _sessionId = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_historyMessagesKey);
    await prefs.remove(_historySessionKey);
    notifyListeners();
  }

  Future<void> _saveHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final completedMessages =
        _messages.where((message) => !message.pending).toList();
    final recentMessages = completedMessages.length > 80
        ? completedMessages.sublist(completedMessages.length - 80)
        : completedMessages;
    await prefs.setString(
      _historyMessagesKey,
      jsonEncode(recentMessages.map((message) => message.toJson()).toList()),
    );
    if (_sessionId == null || _sessionId!.isEmpty) {
      await prefs.remove(_historySessionKey);
    } else {
      await prefs.setString(_historySessionKey, _sessionId!);
    }
  }

  Future<void> connect() async {
    if (_connected) return;
    try {
      _transport = await Future.value(_transportFactory(
        serverUrl: serverUrl,
        sessionToken: sessionToken,
        cloudflareAccessClientId: cloudflareAccessClientId,
        cloudflareAccessClientSecret: cloudflareAccessClientSecret,
      ));
    } catch (error) {
      _error = '자동 연결 오류: $error';
      _connected = false;
      notifyListeners();
      return;
    }
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

  Future<void> sendPrompt(
    String text, {
    String? replyTo,
    String? attachmentName,
    String? attachmentType,
  }) async {
    final prompt = text.trim();
    if (prompt.isEmpty && attachmentName == null) return;
    await connect();
    if (!_connected || _transport == null) return;

    final quotedReply = replyTo?.trim();
    final attachmentLine = attachmentName == null
        ? null
        : '첨부파일: $attachmentName${attachmentType == null ? '' : ' ($attachmentType)'}';
    final payloadText = [
      if (quotedReply != null && quotedReply.isNotEmpty)
        '이전 답변 인용:\n$quotedReply',
      if (attachmentLine != null) attachmentLine,
      prompt,
    ].where((part) => part.trim().isNotEmpty).join('\n\n');

    _messages.add(HermesMessage(
      role: HermesMessageRole.user,
      text: prompt.isEmpty ? attachmentLine! : prompt,
      replyToText: quotedReply?.isEmpty == true ? null : quotedReply,
      attachmentName: attachmentName,
      attachmentType: attachmentType,
      createdAt: DateTime.now(),
    ));
    _sending = true;
    _error = null;
    notifyListeners();
    unawaited(_saveHistory());

    final payload = <String, dynamic>{
      'type': 'prompt.submit',
      'text': payloadText,
      'client': 'flutter',
    };
    if (_sessionId != null) payload['session_id'] = _sessionId;
    _transport!.send(payload);
  }

  void sendApprovalResponse(String approvalId, String choice) {
    if (!_connected || _transport == null) return;
    _transport!.send({
      'type': 'approval.response',
      'id': approvalId,
      'choice': choice,
      'client': 'flutter',
    });
    _messages.add(HermesMessage(
      role: HermesMessageRole.user,
      text: choice,
      replyToText: '승인 요청 $approvalId',
      createdAt: DateTime.now(),
    ));
    notifyListeners();
    unawaited(_saveHistory());
  }

  void _handleEvent(Map<String, dynamic> event) {
    switch (event['type']) {
      case 'message.start':
        _messages.add(const HermesMessage(
            role: HermesMessageRole.assistant, text: '', pending: true));
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
        _messages.add(HermesMessage(
            role: HermesMessageRole.tool,
            text: '${event['summary'] ?? event['name'] ?? '도구 실행 중'}',
            pending: true));
        break;
      case 'tool.complete':
        _messages.add(HermesMessage(
            role: HermesMessageRole.tool, text: '${event['name'] ?? '도구'} 완료'));
        break;
      case 'approval.request':
        _messages.add(HermesMessage(
          role: HermesMessageRole.system,
          text: '${event['text'] ?? '승인이 필요합니다.'}',
          approvalId: event['id']?.toString(),
          choices: event['choices'] is List
              ? (event['choices'] as List)
                  .map((item) => item.toString())
                  .toList()
              : const [],
        ));
        break;
      case 'job.accepted':
        _addJobTimelineMessage(event, HermesJobStatus.accepted);
        break;
      case 'job.progress':
        _addJobTimelineMessage(event, HermesJobStatus.progress);
        break;
      case 'job.completed':
        _addJobTimelineMessage(event, HermesJobStatus.completed);
        _sending = false;
        break;
      case 'job.failed':
        _clearPendingAssistantBubble();
        _addJobTimelineMessage(event, HermesJobStatus.failed);
        _sending = false;
        break;
      case 'error':
        _clearPendingAssistantBubble();
        _error = '${event['message'] ?? '알 수 없는 오류'}';
        _sending = false;
        break;
      default:
        _messages.add(HermesMessage(
            role: HermesMessageRole.system,
            text: '알 수 없는 이벤트: ${event['type']}'));
    }
    notifyListeners();
  }

  void _addJobTimelineMessage(
    Map<String, dynamic> event,
    HermesJobStatus status,
  ) {
    final title = _firstString(event, const [
          'title',
          'summary',
          'name',
          'job_name',
        ]) ??
        '작업';
    final detail = _firstString(event, const [
      'message',
      'text',
      'detail',
      'error',
      'reason',
    ]);
    final progress = _parseProgress(event['progress'] ??
        event['percent'] ??
        event['percentage'] ??
        event['progress_percent']);
    final label = _jobStatusLabel(status);
    _messages.add(HermesMessage(
      role: HermesMessageRole.system,
      text: detail == null || detail.isEmpty ? '$label: $title' : detail,
      createdAt: DateTime.now(),
      jobStatus: status,
      jobId: _firstString(event, const ['job_id', 'jobId', 'id']),
      jobTitle: title,
      jobProgress: progress,
    ));
    unawaited(_saveHistory());
  }

  String? _firstString(Map<String, dynamic> event, List<String> keys) {
    for (final key in keys) {
      final value = event[key];
      if (value == null) continue;
      final text = value.toString().trim();
      if (text.isNotEmpty) return text;
    }
    return null;
  }

  int? _parseProgress(Object? value) {
    final parsed = value is num ? value.round() : int.tryParse('$value');
    if (parsed == null) return null;
    return parsed.clamp(0, 100).toInt();
  }

  String _jobStatusLabel(HermesJobStatus status) => switch (status) {
        HermesJobStatus.accepted => '작업 접수',
        HermesJobStatus.progress => '작업 진행 중',
        HermesJobStatus.completed => '작업 완료',
        HermesJobStatus.failed => '작업 실패',
      };

  void _appendAssistantDelta(String delta) {
    final index = _messages.lastIndexWhere(
        (msg) => msg.role == HermesMessageRole.assistant && msg.pending);
    if (index == -1) {
      _messages.add(HermesMessage(
          role: HermesMessageRole.assistant, text: delta, pending: true));
      return;
    }
    final current = _messages[index];
    _messages[index] = current.copyWith(text: current.text + delta);
  }

  void _clearPendingAssistantBubble() {
    final index = _messages.lastIndexWhere(
        (msg) => msg.role == HermesMessageRole.assistant && msg.pending);
    if (index == -1) return;
    final current = _messages[index];
    if (current.text.trim().isEmpty) {
      _messages.removeAt(index);
    } else {
      _messages[index] = current.copyWith(pending: false);
    }
  }

  void _completeAssistantMessage(String text, {String? sessionId}) {
    if (sessionId != null && sessionId.isNotEmpty) _sessionId = sessionId;
    final index = _messages.lastIndexWhere(
        (msg) => msg.role == HermesMessageRole.assistant && msg.pending);
    if (index == -1) {
      _messages
          .add(HermesMessage(role: HermesMessageRole.assistant, text: text));
    } else {
      _messages[index] = _messages[index].copyWith(text: text, pending: false);
    }
    _sending = false;
    unawaited(_saveHistory());
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _transport?.close();
    super.dispose();
  }
}
