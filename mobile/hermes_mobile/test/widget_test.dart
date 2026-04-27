import 'package:flutter_test/flutter_test.dart';
import 'package:hermes_mobile/app.dart';

void main() {
  testWidgets('Hermes Mobile starts on chat screen and opens settings tab', (tester) async {
    await tester.pumpWidget(const HermesMobileApp());

    expect(find.text('Hermes Mobile'), findsOneWidget);
    expect(find.text('채팅'), findsOneWidget);
    expect(find.text('Hermes에게 메시지 보내기'), findsOneWidget);

    await tester.tap(find.text('설정'));
    await tester.pumpAndSettle();

    expect(find.text('연결 설정'), findsOneWidget);
    expect(find.text('Hermes Console URL'), findsOneWidget);
    expect(find.text('세션 토큰'), findsOneWidget);
  });
}
