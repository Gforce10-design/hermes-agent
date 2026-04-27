import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:hermes_mobile/features/chat/chat_controller.dart';
import 'package:hermes_mobile/features/chat/message_model.dart';
import 'package:hermes_mobile/services/hermes_ws_client.dart';

class FakeTransport implements HermesMessageTransport {
  final StreamController<Map<String, dynamic>> controller = StreamController.broadcast();
  final List<Map<String, dynamic>> sent = [];

  @override
  Stream<Map<String, dynamic>> get events => controller.stream;

  @override
  void send(Map<String, dynamic> payload) => sent.add(payload);

  @override
  Future<void> close() => controller.close();
}

void main() {
  test('sendPrompt sends prompt.submit and records streamed assistant response', () async {
    final fake = FakeTransport();
    final chat = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({required serverUrl, required sessionToken}) => fake,
    );

    await chat.sendPrompt('안녕');
    fake.controller.add({'type': 'message.start', 'session_id': null});
    fake.controller.add({'type': 'message.delta', 'text': '응답'});
    fake.controller.add({'type': 'message.complete', 'session_id': 's1', 'text': '응답'});
    await Future<void>.delayed(Duration.zero);

    expect(fake.sent.single, {'type': 'prompt.submit', 'text': '안녕', 'client': 'flutter'});
    expect(chat.messages.first.role, HermesMessageRole.user);
    expect(chat.messages.first.text, '안녕');
    expect(chat.messages.last.role, HermesMessageRole.assistant);
    expect(chat.messages.last.text, '응답');
    expect(chat.sending, isFalse);
  });

  test('sendPrompt reuses session id returned by previous completion', () async {
    final fake = FakeTransport();
    final chat = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({required serverUrl, required sessionToken}) => fake,
    );

    await chat.sendPrompt('첫 질문');
    fake.controller.add({'type': 'message.start', 'session_id': null});
    fake.controller.add({'type': 'message.complete', 'session_id': 's1', 'text': '첫 응답'});
    await Future<void>.delayed(Duration.zero);

    await chat.sendPrompt('후속 질문');

    expect(fake.sent.last, {
      'type': 'prompt.submit',
      'text': '후속 질문',
      'client': 'flutter',
      'session_id': 's1',
    });
  });

  test('sendPrompt refuses empty session token', () async {
    final chat = ChatController(serverUrl: 'http://localhost:9119', sessionToken: '');

    await chat.sendPrompt('안녕');

    expect(chat.error, '세션 토큰을 입력해 주세요.');
    expect(chat.messages, isEmpty);
  });
}
