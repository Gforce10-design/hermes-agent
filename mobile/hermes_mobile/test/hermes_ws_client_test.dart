import 'package:flutter_test/flutter_test.dart';
import 'package:hermes_mobile/services/hermes_ws_client.dart';

void main() {
  test('buildBootstrapUri targets origin mobile bootstrap endpoint', () {
    final uri = HermesWsClient.buildBootstrapUri(
      serverUrl: 'https://hrs.alpha-mates.com/console',
    );

    expect(uri.toString(), 'https://hrs.alpha-mates.com/api/mobile/bootstrap');
  });

  test(
      'buildMobileWsUri resolves bootstrap mobile ws url against server origin',
      () {
    final uri = HermesWsClient.buildMobileWsUri(
      serverUrl: 'https://hrs.alpha-mates.com/console',
      sessionToken: '',
      mobileWsUrl: '/api/mobile/ws?token=auto-token',
    );

    expect(uri.toString(),
        'wss://hrs.alpha-mates.com/api/mobile/ws?token=auto-token');
  });

  test('buildMobileWsUri keeps token query when manual token is provided', () {
    final uri = HermesWsClient.buildMobileWsUri(
      serverUrl: 'http://localhost:9120',
      sessionToken: 'manual-token',
    );

    expect(
        uri.toString(), 'ws://localhost:9120/api/mobile/ws?token=manual-token');
  });

  test('buildAccessHeaders returns Cloudflare Access service token headers',
      () {
    final headers = HermesWsClient.buildAccessHeaders(
      cloudflareAccessClientId: 'client-id',
      cloudflareAccessClientSecret: 'client-secret',
    );

    expect(headers, {
      'CF-Access-Client-Id': 'client-id',
      'CF-Access-Client-Secret': 'client-secret',
    });
  });

  test('buildAccessHeaders removes copied whitespace from Access fields', () {
    final headers = HermesWsClient.buildAccessHeaders(
      cloudflareAccessClientId: ' client\n-id ',
      cloudflareAccessClientSecret: ' client\t-secret ',
    );

    expect(headers, {
      'CF-Access-Client-Id': 'client-id',
      'CF-Access-Client-Secret': 'client-secret',
    });
  });

  test('buildAccessHeaders omits blank Cloudflare Access fields', () {
    final headers = HermesWsClient.buildAccessHeaders(
      cloudflareAccessClientId: 'client-id',
      cloudflareAccessClientSecret: '',
    );

    expect(headers, isEmpty);
  });

  test('buildAccessDiagnostics reports only safe metadata', () {
    final diagnostics = HermesWsClient.buildAccessDiagnostics(
      serverUrl: 'https://hrs.alpha-mates.com/console',
      cloudflareAccessClientId: ' client\n-id ',
      cloudflareAccessClientSecret: ' secret\t-value ',
    );

    expect(diagnostics.clientIdPresent, isTrue);
    expect(diagnostics.clientSecretPresent, isTrue);
    expect(diagnostics.clientIdLength, 9);
    expect(diagnostics.clientSecretLength, 12);
    expect(diagnostics.headersPresent, isTrue);
    expect(diagnostics.bootstrapUri.toString(),
        'https://hrs.alpha-mates.com/api/mobile/bootstrap');
    expect(diagnostics.safeSummary, contains('Access 헤더 생성됨'));
    expect(diagnostics.safeSummary, isNot(contains('client-id')));
    expect(diagnostics.safeSummary, isNot(contains('secret-value')));
  });

  test('describeBootstrapFailure includes redirect host without token values',
      () {
    final message = HermesWsClient.describeBootstrapFailure(
      statusCode: 302,
      location: 'https://alpha-mates.cloudflareaccess.com/cdn-cgi/access/login',
    );

    expect(message, contains('Cloudflare Access'));
    expect(message, contains('Service Token'));
    expect(message, contains('alpha-mates.cloudflareaccess.com'));
  });

  test('describeBootstrapFailure explains forbidden Access policy', () {
    final message = HermesWsClient.describeBootstrapFailure(statusCode: 403);

    expect(message, contains('403'));
    expect(message, contains('정책'));
  });
}
