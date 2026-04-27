import 'package:flutter/material.dart';

import 'chat_controller.dart';
import 'message_model.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({
    required this.serverUrl,
    required this.sessionToken,
    super.key,
  });

  final String serverUrl;
  final String sessionToken;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  late ChatController _controller;
  final _inputController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _controller = ChatController(serverUrl: widget.serverUrl, sessionToken: widget.sessionToken);
  }

  @override
  void didUpdateWidget(covariant ChatScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.serverUrl != widget.serverUrl || oldWidget.sessionToken != widget.sessionToken) {
      _controller.dispose();
      _controller = ChatController(serverUrl: widget.serverUrl, sessionToken: widget.sessionToken);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _inputController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return Column(
          children: [
            _ConnectionBanner(controller: _controller),
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.all(12),
                itemCount: _controller.messages.length,
                itemBuilder: (context, index) => _MessageBubble(message: _controller.messages[index]),
              ),
            ),
            if (_controller.error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Text(_controller.error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _inputController,
                        minLines: 1,
                        maxLines: 4,
                        decoration: const InputDecoration(
                          hintText: 'Hermes에게 메시지 보내기',
                          border: OutlineInputBorder(),
                        ),
                        onSubmitted: (_) => _send(),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton.filled(
                      onPressed: _controller.sending ? null : _send,
                      icon: _controller.sending
                          ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Icon(Icons.send),
                    ),
                  ],
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  void _send() {
    final text = _inputController.text;
    _inputController.clear();
    _controller.sendPrompt(text);
  }
}

class _ConnectionBanner extends StatelessWidget {
  const _ConnectionBanner({required this.controller});

  final ChatController controller;

  @override
  Widget build(BuildContext context) {
    final color = controller.connected ? Colors.tealAccent : Colors.amberAccent;
    final text = controller.connected ? '연결됨' : '설정에서 토큰 입력 후 첫 메시지 전송 시 연결';
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      color: color.withValues(alpha: 0.12),
      child: Text(text),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final HermesMessage message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == HermesMessageRole.user;
    final alignment = isUser ? Alignment.centerRight : Alignment.centerLeft;
    final color = switch (message.role) {
      HermesMessageRole.user => Theme.of(context).colorScheme.primaryContainer,
      HermesMessageRole.assistant => Theme.of(context).colorScheme.surfaceContainerHighest,
      HermesMessageRole.tool => Theme.of(context).colorScheme.tertiaryContainer,
      HermesMessageRole.system => Theme.of(context).colorScheme.secondaryContainer,
    };
    return Align(
      alignment: alignment,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 340),
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(16)),
        child: Text(message.pending && message.text.isEmpty ? '응답 대기 중...' : message.text),
      ),
    );
  }
}
