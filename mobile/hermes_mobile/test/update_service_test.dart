import 'package:flutter_test/flutter_test.dart';
import 'package:hermes_mobile/features/update/update_service.dart';

void main() {
  test('buildUpdateUri targets origin mobile update endpoint', () {
    final uri = AppUpdateService.buildUpdateUri(
      serverUrl: 'https://hrs.alpha-mates.com/console',
    );

    expect(uri.toString(), 'https://hrs.alpha-mates.com/api/mobile/app-update');
  });

  test('AppUpdateInfo detects newer build', () {
    final info = AppUpdateInfo.fromJson({
      'version': '0.2.0',
      'build': 2,
      'apk_url': 'https://hrs.alpha-mates.com/api/mobile/app-release/apk',
      'notes': '기존 앱을 삭제하지 말고 업데이트하세요.',
    });

    expect(info.isNewerThan(1), isTrue);
    expect(info.isNewerThan(2), isFalse);
    expect(info.notes, contains('삭제하지 말고'));
  });
}
