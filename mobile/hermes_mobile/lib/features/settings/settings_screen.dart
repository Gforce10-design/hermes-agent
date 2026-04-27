import 'package:flutter/material.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({
    required this.serverUrl,
    required this.sessionToken,
    required this.onChanged,
    super.key,
  });

  final String serverUrl;
  final String sessionToken;
  final void Function(String serverUrl, String sessionToken) onChanged;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _serverController;
  late final TextEditingController _tokenController;

  @override
  void initState() {
    super.initState();
    _serverController = TextEditingController(text: widget.serverUrl);
    _tokenController = TextEditingController(text: widget.sessionToken);
  }

  @override
  void dispose() {
    _serverController.dispose();
    _tokenController.dispose();
    super.dispose();
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
            labelText: '세션 토큰',
            border: OutlineInputBorder(),
          ),
          obscureText: true,
        ),
        const SizedBox(height: 16),
        FilledButton(
          onPressed: () => widget.onChanged(_serverController.text.trim(), _tokenController.text.trim()),
          child: const Text('저장'),
        ),
        const SizedBox(height: 24),
        const Text('현재 MVP는 /api/mobile/ws WebSocket에 연결합니다. Cloudflare Access/OAuth 저장은 다음 단계에서 추가합니다.'),
      ],
    );
  }
}
