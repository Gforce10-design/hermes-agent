import 'package:flutter/material.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({
    required this.serverUrl,
    required this.sessionToken,
    required this.cloudflareAccessClientId,
    required this.cloudflareAccessClientSecret,
    required this.onChanged,
    required this.onTestConnection,
    required this.onCheckUpdate,
    required this.onOpenUpdate,
    super.key,
  });

  final String serverUrl;
  final String sessionToken;
  final String cloudflareAccessClientId;
  final String cloudflareAccessClientSecret;
  final Future<void> Function(
    String serverUrl,
    String sessionToken,
    String cloudflareAccessClientId,
    String cloudflareAccessClientSecret,
  ) onChanged;
  final Future<String> Function(
    String serverUrl,
    String cloudflareAccessClientId,
    String cloudflareAccessClientSecret,
  ) onTestConnection;
  final Future<String> Function(
    String serverUrl,
    String cloudflareAccessClientId,
    String cloudflareAccessClientSecret,
  ) onCheckUpdate;
  final Future<String> Function() onOpenUpdate;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _serverController;
  late final TextEditingController _tokenController;
  late final TextEditingController _accessClientIdController;
  late final TextEditingController _accessClientSecretController;
  bool _saving = false;
  bool _testing = false;
  bool _checkingUpdate = false;
  bool _openingUpdate = false;
  String _lastTestMessage = '';
  String _lastUpdateMessage = '';

  @override
  void initState() {
    super.initState();
    _serverController = TextEditingController(text: widget.serverUrl);
    _tokenController = TextEditingController(text: widget.sessionToken);
    _accessClientIdController =
        TextEditingController(text: widget.cloudflareAccessClientId);
    _accessClientSecretController =
        TextEditingController(text: widget.cloudflareAccessClientSecret);
  }

  @override
  void didUpdateWidget(covariant SettingsScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.cloudflareAccessClientId != widget.cloudflareAccessClientId) {
      _accessClientIdController.text = widget.cloudflareAccessClientId;
    }
    if (oldWidget.cloudflareAccessClientSecret !=
        widget.cloudflareAccessClientSecret) {
      _accessClientSecretController.text = widget.cloudflareAccessClientSecret;
    }
  }

  @override
  void dispose() {
    _serverController.dispose();
    _tokenController.dispose();
    _accessClientIdController.dispose();
    _accessClientSecretController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    await widget.onChanged(
      _serverController.text.trim(),
      _tokenController.text.trim(),
      _accessClientIdController.text.trim(),
      _accessClientSecretController.text.trim(),
    );
    if (!mounted) return;
    setState(() => _saving = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('설정을 저장했습니다.')),
    );
  }

  Future<void> _testConnection() async {
    setState(() => _testing = true);
    final message = await widget.onTestConnection(
      _serverController.text.trim(),
      _accessClientIdController.text.trim(),
      _accessClientSecretController.text.trim(),
    );
    if (!mounted) return;
    setState(() {
      _testing = false;
      _lastTestMessage = message;
    });
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _checkUpdate() async {
    setState(() => _checkingUpdate = true);
    final message = await widget.onCheckUpdate(
      _serverController.text.trim(),
      _accessClientIdController.text.trim(),
      _accessClientSecretController.text.trim(),
    );
    if (!mounted) return;
    setState(() {
      _checkingUpdate = false;
      _lastUpdateMessage = message;
    });
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _openUpdate() async {
    setState(() => _openingUpdate = true);
    final message = await widget.onOpenUpdate();
    if (!mounted) return;
    setState(() {
      _openingUpdate = false;
      _lastUpdateMessage = message;
    });
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('연결 설정', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 16),
        TextField(
          controller: _serverController,
          decoration: const InputDecoration(
            labelText: 'Hermes Console URL',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _tokenController,
          decoration: const InputDecoration(
            labelText: '수동 세션 토큰(선택)',
            helperText: '비워두면 모바일 자동 연결을 사용합니다.',
            border: OutlineInputBorder(),
          ),
          obscureText: true,
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _accessClientIdController,
          decoration: const InputDecoration(
            labelText: 'Cloudflare Access Client ID(선택)',
            helperText: '외부망에서 Access 보호를 통과할 때 사용합니다.',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _accessClientSecretController,
          decoration: const InputDecoration(
            labelText: 'Cloudflare Access Client Secret(선택)',
            helperText: 'Service Token의 Secret입니다.',
            border: OutlineInputBorder(),
          ),
          obscureText: true,
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: FilledButton(
                onPressed: _saving ? null : _save,
                child: Text(_saving ? '저장 중...' : '저장'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton(
                onPressed: _testing ? null : _testConnection,
                child: Text(_testing ? '확인 중...' : '연결 테스트'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
        if (_lastTestMessage.isNotEmpty) ...[
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(_lastTestMessage),
            ),
          ),
          const SizedBox(height: 16),
        ],
        Text('앱 업데이트', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        const Text('새 버전이 있으면 기존 앱을 지우지 말고 Android 설치 화면에서 “업데이트”를 선택하세요.'),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: _checkingUpdate ? null : _checkUpdate,
                child: Text(_checkingUpdate ? '확인 중...' : '업데이트 확인'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FilledButton.tonal(
                onPressed: _openingUpdate ? null : _openUpdate,
                child: Text(_openingUpdate ? '여는 중...' : '업데이트 열기'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (_lastUpdateMessage.isNotEmpty) ...[
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(_lastUpdateMessage),
            ),
          ),
          const SizedBox(height: 16),
        ],
        const Text(
            '토큰을 비워두면 /api/mobile/bootstrap에서 자동 연결 정보를 받아 /api/mobile/ws에 연결합니다. 외부망에서 Cloudflare Access가 켜져 있으면 Access Service Token도 입력하세요.'),
      ],
    );
  }
}
