import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hermes_mobile/app.dart';
import 'package:hermes_mobile/features/settings/settings_screen.dart';
import 'package:hermes_mobile/services/hermes_rest_client.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _FakeStatusService implements HermesStatusService {
  _FakeStatusService({this.error});

  final Object? error;
  int calls = 0;

  @override
  Future<MobileStatusSnapshot> fetchStatus({
    required String serverUrl,
    required String sessionToken,
    required String cloudflareAccessClientId,
    required String cloudflareAccessClientSecret,
  }) async {
    calls += 1;
    if (error != null) throw error!;
    return const MobileStatusSnapshot(
      generatedAt: '2026-04-29T06:35:00Z',
      hermes: HermesServiceStatus(
        service: 'Hermes Agent',
        state: 'running',
        detail: 'Gateway running; active sessions 1',
      ),
      mobileApi: MobileApiStatus(
        state: 'online',
        auth: 'cloudflare_access_service_token',
        detail: '인증된 읽기 전용 모바일 상태 API',
      ),
      alphaMate: AlphaMateStatus(
        state: 'placeholder',
        summary: 'AlphaMate 로컬 운영 신호를 표시 중입니다.',
        detail: '원격 G3 점검 미실행',
      ),
      notifications: [
        HermesNotification(
          id: 'n1',
          severity: 'info',
          title: '모바일 API 연결됨',
          message: '상태 조회 API가 응답했습니다.',
          createdAt: '2026-04-29T06:35:00Z',
        ),
      ],
    );
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('Hermes Mobile starts with richer console navigation',
      (tester) async {
    await tester.pumpWidget(const HermesMobileApp());
    await tester.pumpAndSettle();

    expect(find.text('Hermes Mobile'), findsOneWidget);
    expect(find.text('홈'), findsOneWidget);
    expect(find.text('채팅'), findsOneWidget);
    expect(find.text('멀티에이전트'), findsOneWidget);
    expect(find.text('상태'), findsOneWidget);
    expect(find.text('설정'), findsOneWidget);
    expect(find.text('오늘의 Hermes'), findsOneWidget);
    expect(find.text('빠른 작업'), findsOneWidget);
  });

  testWidgets('chat draft is preserved when switching tabs', (tester) async {
    await tester.pumpWidget(const HermesMobileApp());
    await tester.pumpAndSettle();

    await tester.tap(find.text('채팅'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, '탭 이동 후에도 남아야 합니다');

    await tester.tap(find.text('홈'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('채팅'));
    await tester.pumpAndSettle();

    expect(find.text('탭 이동 후에도 남아야 합니다'), findsOneWidget);
  });

  testWidgets('chat renders restored job timeline cards with Korean labels',
      (tester) async {
    SharedPreferences.setMockInitialValues({
      'chat.history.messages':
          '[{"role":"system","text":"테스트 실행 중","jobStatus":"progress","jobId":"job-1","jobTitle":"배포 작업","jobProgress":65}]',
    });

    await tester.pumpWidget(const HermesMobileApp());
    await tester.pumpAndSettle();
    await tester.tap(find.text('채팅'));
    await tester.pumpAndSettle();

    expect(find.text('작업 진행 중'), findsOneWidget);
    expect(find.text('배포 작업'), findsOneWidget);
    expect(find.textContaining('65%'), findsOneWidget);
    expect(find.text('테스트 실행 중'), findsOneWidget);
  });

  testWidgets('multi-agent tab shows codex primary and opus fallback agents',
      (tester) async {
    await tester.pumpWidget(const HermesMobileApp());
    await tester.pumpAndSettle();

    await tester.tap(find.text('멀티에이전트'));
    await tester.pumpAndSettle();

    expect(find.text('멀티에이전트'), findsWidgets);
    expect(find.text('Codex OAuth'), findsOneWidget);
    expect(find.text('Claude CLI Opus 4.7'), findsOneWidget);
    expect(find.text('Hermes 운영'), findsOneWidget);
    expect(find.text('AlphaMate 운영'), findsOneWidget);
  });

  testWidgets('status tab loads real mobile status cards with Korean labels',
      (tester) async {
    final fakeStatus = _FakeStatusService();
    await tester.pumpWidget(HermesMobileApp(statusService: fakeStatus));
    await tester.pumpAndSettle();

    await tester.tap(find.text('상태'));
    await tester.pumpAndSettle();

    expect(fakeStatus.calls, 1);
    expect(find.text('운영 상태'), findsOneWidget);
    expect(find.text('Hermes'), findsOneWidget);
    expect(find.text('모바일 API'), findsOneWidget);
    expect(find.text('AlphaMate'), findsOneWidget);
    expect(find.text('알림함'), findsOneWidget);
    expect(find.textContaining('실행 중'), findsOneWidget);
    expect(find.textContaining('Access 서비스 토큰'), findsOneWidget);
    expect(find.textContaining('원격 G3 점검 미실행'), findsOneWidget);
    expect(find.textContaining('모바일 API 연결됨'), findsOneWidget);
  });

  testWidgets('status tab shows fetch errors and refresh affordance',
      (tester) async {
    await tester.pumpWidget(HermesMobileApp(
      statusService: _FakeStatusService(error: StateError('인증 실패')),
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.text('상태'));
    await tester.pumpAndSettle();

    expect(find.text('상태 조회 실패'), findsOneWidget);
    expect(find.textContaining('인증 실패'), findsOneWidget);
    expect(find.byTooltip('새로고침'), findsOneWidget);
  });

  testWidgets('settings save gives visible feedback and keeps values',
      (tester) async {
    await tester.pumpWidget(const HermesMobileApp());
    await tester.pumpAndSettle();

    await tester.tap(find.text('설정'));
    await tester.pumpAndSettle();

    expect(find.text('연결 설정'), findsOneWidget);
    expect(find.text('Hermes Console URL'), findsOneWidget);
    expect(find.text('수동 세션 토큰(선택)'), findsOneWidget);
    expect(find.text('Cloudflare Access Client ID(선택)'), findsOneWidget);
    expect(find.text('Cloudflare Access Client Secret(선택)'), findsOneWidget);
    expect(find.text('연결 테스트'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('업데이트 확인'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('업데이트 확인'), findsOneWidget);

    await tester.enterText(
        find.bySemanticsLabel('Cloudflare Access Client ID(선택)'), 'client-id');
    await tester.enterText(
        find.bySemanticsLabel('Cloudflare Access Client Secret(선택)'),
        'client-secret');
    await tester.tap(find.text('저장'));
    await tester.pump();

    expect(find.text('설정을 저장했습니다.'), findsOneWidget);

    await tester.tap(find.text('홈'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('설정'));
    await tester.pumpAndSettle();

    expect(find.text('client-id'), findsOneWidget);
  });

  testWidgets('settings connection test displays safe diagnostics',
      (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: SettingsScreen(
          serverUrl: 'https://hrs.alpha-mates.com/console',
          sessionToken: '',
          cloudflareAccessClientId: 'client-id',
          cloudflareAccessClientSecret: 'client-secret',
          onChanged: (_, __, ___, ____) async {},
          onTestConnection: (_, __, ___) async =>
              '진단: Access 헤더 생성됨 · Client ID 9자 · Secret 13자 · 요청 https://hrs.alpha-mates.com/api/mobile/bootstrap\n연결 테스트 실패: Cloudflare Access 로그인으로 이동했습니다. redirect host: alpha-mates.cloudflareaccess.com (302)',
          onCheckUpdate: (_, __, ___) async => '업데이트 가능: 0.1.0+1 → 0.2.0+2',
          onOpenUpdate: () async => '업데이트 파일을 열었습니다.',
        ),
      ),
    ));

    await tester.tap(find.text('연결 테스트'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Access 헤더 생성됨'), findsWidgets);
    expect(
        find.textContaining('redirect host: alpha-mates.cloudflareaccess.com'),
        findsWidgets);
    expect(find.textContaining('secret-value'), findsNothing);
  });
  testWidgets('settings update check explains in-place update', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: SettingsScreen(
          serverUrl: 'https://hrs.alpha-mates.com/console',
          sessionToken: '',
          cloudflareAccessClientId: 'client-id',
          cloudflareAccessClientSecret: 'client-secret',
          onChanged: (_, __, ___, ____) async {},
          onTestConnection: (_, __, ___) async => '연결 테스트 성공',
          onCheckUpdate: (_, __, ___) async => '업데이트 가능: 0.1.0+1 → 0.2.0+2',
          onOpenUpdate: () async =>
              '업데이트 파일을 열었습니다. Android 설치 화면에서 “업데이트”를 선택하세요.',
        ),
      ),
    ));

    await tester.scrollUntilVisible(
      find.text('업데이트 확인'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('업데이트 확인'));
    await tester.pumpAndSettle();

    expect(find.textContaining('업데이트 가능'), findsWidgets);
    expect(find.textContaining('기존 앱을 지우지 말고'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('업데이트 열기'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('업데이트 열기'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Android 설치 화면'), findsWidgets);
  });
}
