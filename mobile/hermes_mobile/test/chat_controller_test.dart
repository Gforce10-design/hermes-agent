import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:hermes_mobile/features/chat/chat_controller.dart';
import 'package:hermes_mobile/features/chat/message_model.dart';
import 'package:hermes_mobile/services/hermes_ws_client.dart';
import 'package:shared_preferences/shared_preferences.dart';

class FakeTransport implements HermesMessageTransport {
  final StreamController<Map<String, dynamic>> controller =
      StreamController.broadcast();
  final List<Map<String, dynamic>> sent = [];

  @override
  Stream<Map<String, dynamic>> get events => controller.stream;

  @override
  void send(Map<String, dynamic> payload) => sent.add(payload);

  @override
  Future<void> close() => controller.close();
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('sendPrompt sends prompt.submit and records streamed assistant response',
      () async {
    final fake = FakeTransport();
    final chat = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({
        required serverUrl,
        required sessionToken,
        required cloudflareAccessClientId,
        required cloudflareAccessClientSecret,
      }) =>
          fake,
    );

    await chat.sendPrompt('안녕');
    fake.controller.add({'type': 'message.start', 'session_id': null});
    fake.controller.add({'type': 'message.delta', 'text': '응답'});
    fake.controller
        .add({'type': 'message.complete', 'session_id': 's1', 'text': '응답'});
    await Future<void>.delayed(Duration.zero);

    expect(fake.sent.single,
        {'type': 'prompt.submit', 'text': '안녕', 'client': 'flutter'});
    expect(chat.messages.first.role, HermesMessageRole.user);
    expect(chat.messages.first.text, '안녕');
    expect(chat.messages.last.role, HermesMessageRole.assistant);
    expect(chat.messages.last.text, '응답');
    expect(chat.sending, isFalse);
  });

  test('sendPrompt reuses session id returned by previous completion',
      () async {
    final fake = FakeTransport();
    final chat = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({
        required serverUrl,
        required sessionToken,
        required cloudflareAccessClientId,
        required cloudflareAccessClientSecret,
      }) =>
          fake,
    );

    await chat.sendPrompt('첫 질문');
    fake.controller.add({'type': 'message.start', 'session_id': null});
    fake.controller
        .add({'type': 'message.complete', 'session_id': 's1', 'text': '첫 응답'});
    await Future<void>.delayed(Duration.zero);

    await chat.sendPrompt('후속 질문');

    expect(fake.sent.last, {
      'type': 'prompt.submit',
      'text': '후속 질문',
      'client': 'flutter',
      'session_id': 's1',
    });
  });

  test('completed messages and session id are restored from local history',
      () async {
    final fake = FakeTransport();
    final chat = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({
        required serverUrl,
        required sessionToken,
        required cloudflareAccessClientId,
        required cloudflareAccessClientSecret,
      }) =>
          fake,
    );

    await chat.restoreHistory();
    await chat.sendPrompt('첫 질문');
    fake.controller.add({'type': 'message.start', 'session_id': null});
    fake.controller
        .add({'type': 'message.complete', 'session_id': 's1', 'text': '첫 응답'});
    await Future<void>.delayed(Duration.zero);

    final restored = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({
        required serverUrl,
        required sessionToken,
        required cloudflareAccessClientId,
        required cloudflareAccessClientSecret,
      }) =>
          fake,
    );
    await restored.restoreHistory();
    await restored.sendPrompt('후속 질문');

    expect(restored.messages.map((message) => message.text),
        containsAllInOrder(['첫 질문', '첫 응답', '후속 질문']));
    expect(fake.sent.last['session_id'], 's1');
  });

  test('sendPrompt can include a quoted reply context', () async {
    final fake = FakeTransport();
    final chat = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({
        required serverUrl,
        required sessionToken,
        required cloudflareAccessClientId,
        required cloudflareAccessClientSecret,
      }) =>
          fake,
    );

    await chat.sendPrompt('자세히 설명해줘', replyTo: '이전 답변 내용');

    expect(fake.sent.single['text'], contains('이전 답변 내용'));
    expect(fake.sent.single['text'], contains('자세히 설명해줘'));
    expect(chat.messages.single.replyToText, '이전 답변 내용');
  });

  test('sendPrompt can include attachment metadata', () async {
    final fake = FakeTransport();
    final chat = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({
        required serverUrl,
        required sessionToken,
        required cloudflareAccessClientId,
        required cloudflareAccessClientSecret,
      }) =>
          fake,
    );

    await chat.sendPrompt('이 파일 확인해줘',
        attachmentName: 'report.pdf', attachmentType: 'pdf');

    expect(fake.sent.single['text'], contains('첨부파일: report.pdf (pdf)'));
    expect(fake.sent.single['text'], contains('이 파일 확인해줘'));
    expect(chat.messages.single.attachmentName, 'report.pdf');
  });

  test('approval request records choices and sends selected answer', () async {
    final fake = FakeTransport();
    final chat = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({
        required serverUrl,
        required sessionToken,
        required cloudflareAccessClientId,
        required cloudflareAccessClientSecret,
      }) =>
          fake,
    );

    await chat.connect();
    fake.controller.add({
      'type': 'approval.request',
      'id': 'approval-1',
      'text': '진행할까요?',
      'choices': ['1 승인', '2 보류'],
    });
    await Future<void>.delayed(Duration.zero);

    expect(chat.messages.last.approvalId, 'approval-1');
    expect(chat.messages.last.choices, ['1 승인', '2 보류']);

    chat.sendApprovalResponse('approval-1', '1 승인');

    expect(fake.sent.last, {
      'type': 'approval.response',
      'id': 'approval-1',
      'choice': '1 승인',
      'client': 'flutter',
    });
  });

  test('job.failed removes blank pending assistant bubble from message.start',
      () async {
    final fake = FakeTransport();
    final chat = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({
        required serverUrl,
        required sessionToken,
        required cloudflareAccessClientId,
        required cloudflareAccessClientSecret,
      }) =>
          fake,
    );

    await chat.connect();
    fake.controller.add({'type': 'message.start'});
    fake.controller.add({
      'type': 'job.failed',
      'job_id': 'job-1',
      'title': '배포 작업',
      'message': '작업 처리에 실패했습니다',
    });
    await Future<void>.delayed(Duration.zero);

    expect(
      chat.messages.where((message) =>
          message.role == HermesMessageRole.assistant &&
          message.pending &&
          message.text.isEmpty),
      isEmpty,
    );
    expect(chat.messages.where((message) => message.pending), isEmpty);
    expect(chat.messages.single.jobStatus, HermesJobStatus.failed);
    expect(chat.messages.single.text, '작업 처리에 실패했습니다');
    expect(chat.sending, isFalse);
  });

  test('error removes blank pending assistant bubble from message.start',
      () async {
    final fake = FakeTransport();
    final chat = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({
        required serverUrl,
        required sessionToken,
        required cloudflareAccessClientId,
        required cloudflareAccessClientSecret,
      }) =>
          fake,
    );

    await chat.connect();
    fake.controller.add({'type': 'message.start'});
    fake.controller.add({'type': 'error', 'message': '서버 오류'});
    await Future<void>.delayed(Duration.zero);

    expect(chat.messages, isEmpty);
    expect(chat.error, '서버 오류');
    expect(chat.sending, isFalse);
  });

  test('job websocket events are stored as durable timeline messages',
      () async {
    final fake = FakeTransport();
    final chat = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({
        required serverUrl,
        required sessionToken,
        required cloudflareAccessClientId,
        required cloudflareAccessClientSecret,
      }) =>
          fake,
    );

    await chat.connect();
    fake.controller.add({
      'type': 'job.accepted',
      'job_id': 'job-1',
      'title': '배포 작업',
      'message': '대기열에 등록됨',
    });
    fake.controller.add({
      'type': 'job.progress',
      'job_id': 'job-1',
      'title': '배포 작업',
      'progress': 40,
      'message': '테스트 실행 중',
    });
    fake.controller.add({
      'type': 'job.completed',
      'job_id': 'job-1',
      'title': '배포 작업',
      'message': '배포 완료',
    });
    await Future<void>.delayed(Duration.zero);

    final jobs = chat.messages.where((message) => message.isJob).toList();
    expect(jobs.map((message) => message.jobStatus), [
      HermesJobStatus.accepted,
      HermesJobStatus.progress,
      HermesJobStatus.completed,
    ]);
    expect(jobs[1].jobId, 'job-1');
    expect(jobs[1].jobTitle, '배포 작업');
    expect(jobs[1].jobProgress, 40);
    expect(jobs[1].text, contains('테스트 실행 중'));

    final restored = ChatController(
      serverUrl: 'http://localhost:9119',
      sessionToken: 'token',
      transportFactory: ({
        required serverUrl,
        required sessionToken,
        required cloudflareAccessClientId,
        required cloudflareAccessClientSecret,
      }) =>
          fake,
    );
    await Future<void>.delayed(Duration.zero);
    await restored.restoreHistory();

    expect(restored.messages.where((message) => message.isJob).length, 3);
    expect(restored.messages.last.jobStatus, HermesJobStatus.completed);
  });

  test('connect passes Cloudflare Access service token settings to transport',
      () async {
    final fake = FakeTransport();
    late String capturedClientId;
    late String capturedClientSecret;
    final chat = ChatController(
      serverUrl: 'https://hrs.alpha-mates.com',
      sessionToken: '',
      cloudflareAccessClientId: 'client-id',
      cloudflareAccessClientSecret: 'client-secret',
      transportFactory: ({
        required serverUrl,
        required sessionToken,
        required cloudflareAccessClientId,
        required cloudflareAccessClientSecret,
      }) {
        capturedClientId = cloudflareAccessClientId;
        capturedClientSecret = cloudflareAccessClientSecret;
        return fake;
      },
    );

    await chat.sendPrompt('안녕');

    expect(capturedClientId, 'client-id');
    expect(capturedClientSecret, 'client-secret');
    expect(fake.sent.single,
        {'type': 'prompt.submit', 'text': '안녕', 'client': 'flutter'});
  });
}
