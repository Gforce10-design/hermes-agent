import 'dart:convert';
import 'dart:io';

import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/hermes_ws_client.dart';

class AppUpdateInfo {
  const AppUpdateInfo({
    required this.version,
    required this.build,
    required this.apkUrl,
    required this.notes,
  });

  final String version;
  final int build;
  final String apkUrl;
  final String notes;

  bool isNewerThan(int currentBuild) => build > currentBuild;

  factory AppUpdateInfo.fromJson(Map<String, dynamic> json) {
    return AppUpdateInfo(
      version: '${json['version'] ?? ''}',
      build: int.tryParse('${json['build'] ?? '0'}') ?? 0,
      apkUrl: '${json['apk_url'] ?? ''}',
      notes: '${json['notes'] ?? ''}',
    );
  }
}

class AppUpdateResult {
  const AppUpdateResult({
    required this.currentVersion,
    required this.currentBuild,
    required this.latest,
  });

  final String currentVersion;
  final int currentBuild;
  final AppUpdateInfo latest;

  bool get updateAvailable => latest.isNewerThan(currentBuild);

  String get userMessage {
    if (updateAvailable) {
      return '업데이트 가능: $currentVersion+$currentBuild → ${latest.version}+${latest.build}\n${latest.notes}';
    }
    return '현재 최신 버전입니다: $currentVersion+$currentBuild';
  }
}

class AppUpdateService {
  static Uri buildUpdateUri({required String serverUrl}) {
    final origin = HermesWsClient.parseServerOrigin(serverUrl);
    return origin.replace(
        path: '/api/mobile/app-update', query: null, fragment: null);
  }

  static Future<AppUpdateResult> checkLatest({
    required String serverUrl,
    required String cloudflareAccessClientId,
    required String cloudflareAccessClientSecret,
  }) async {
    final packageInfo = await PackageInfo.fromPlatform();
    final currentBuild = int.tryParse(packageInfo.buildNumber) ?? 0;
    final updateUri = buildUpdateUri(serverUrl: serverUrl);
    final headers = HermesWsClient.buildAccessHeaders(
      cloudflareAccessClientId: cloudflareAccessClientId,
      cloudflareAccessClientSecret: cloudflareAccessClientSecret,
    );

    final client = HttpClient();
    try {
      final request = await client.getUrl(updateUri);
      request.followRedirects = false;
      headers.forEach(request.headers.set);
      final response = await request.close();
      final body = await response.transform(utf8.decoder).join();
      if (response.statusCode != HttpStatus.ok) {
        throw StateError(HermesWsClient.describeBootstrapFailure(
          statusCode: response.statusCode,
          location: response.headers.value(HttpHeaders.locationHeader),
        ));
      }
      final latest =
          AppUpdateInfo.fromJson(jsonDecode(body) as Map<String, dynamic>);
      return AppUpdateResult(
        currentVersion: packageInfo.version,
        currentBuild: currentBuild,
        latest: latest,
      );
    } finally {
      client.close(force: true);
    }
  }

  static Future<void> openUpdate(AppUpdateInfo info) async {
    final uri = Uri.parse(info.apkUrl);
    final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!opened) {
      throw StateError('업데이트 다운로드 화면을 열 수 없습니다.');
    }
  }
}
