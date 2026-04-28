import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hermes_mobile/app.dart';
import 'package:hermes_mobile/features/settings/settings_screen.dart';
import 'package:shared_preferences/shared_preferences.dart';

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
