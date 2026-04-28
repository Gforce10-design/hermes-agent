import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'chat_controller.dart';
import 'message_model.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({
    required this.serverUrl,
    required this.sessionToken,
    required this.cloudflareAccessClientId,
    required this.cloudflareAccessClientSecret,
    super.key,
  });

  final String serverUrl;
  final String sessionToken;
  final String cloudflareAccessClientId;
  final String cloudflareAccessClientSecret;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  late ChatController _controller;
  final _inputController = TextEditingController();
  String? _replyToText;
  String? _attachmentName;
  String? _attachmentType;

  @override
  void initState() {
    super.initState();
    _controller = ChatController(
      serverUrl: widget.serverUrl,
      sessionToken: widget.sessionToken,
      cloudflareAccessClientId: widget.cloudflareAccessClientId,
      cloudflareAccessClientSecret: widget.cloudflareAccessClientSecret,
    );
    _controller.restoreHistory();
  }

  @override
  void didUpdateWidget(covariant ChatScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.serverUrl != widget.serverUrl ||
        oldWidget.sessionToken != widget.sessionToken ||
        oldWidget.cloudflareAccessClientId != widget.cloudflareAccessClientId ||
        oldWidget.cloudflareAccessClientSecret !=
            widget.cloudflareAccessClientSecret) {
      _controller.dispose();
      _controller = ChatController(
        serverUrl: widget.serverUrl,
        sessionToken: widget.sessionToken,
        cloudflareAccessClientId: widget.cloudflareAccessClientId,
        cloudflareAccessClientSecret: widget.cloudflareAccessClientSecret,
      );
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
                itemBuilder: (context, index) => _MessageBubble(
                  message: _controller.messages[index],
                  onCopy: _copyMessage,
                  onReply: _startReply,
                  onApprovalChoice: _controller.sendApprovalResponse,
                ),
              ),
            ),
            if (_controller.error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Text(_controller.error!,
                    style:
                        TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (_replyToText != null)
                      _ComposerChip(
                        icon: Icons.reply,
                        label: '답장: ${_shorten(_replyToText!)}',
                        onClear: () => setState(() => _replyToText = null),
                      ),
                    if (_attachmentName != null)
                      _ComposerChip(
                        icon: Icons.attach_file,
                        label: '첨부: $_attachmentName',
                        onClear: () => setState(() {
                          _attachmentName = null;
                          _attachmentType = null;
                        }),
                      ),
                    Row(
                      children: [
                        IconButton(
                          tooltip: '첨부파일',
                          onPressed: _pickAttachment,
                          icon: const Icon(Icons.attach_file),
                        ),
                        IconButton(
                          tooltip: '붙여넣기',
                          onPressed: _pasteFromClipboard,
                          icon: const Icon(Icons.content_paste),
                        ),
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
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child:
                                      CircularProgressIndicator(strokeWidth: 2))
                              : const Icon(Icons.send),
                        ),
                      ],
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
    final replyTo = _replyToText;
    final attachmentName = _attachmentName;
    final attachmentType = _attachmentType;
    setState(() {
      _replyToText = null;
      _attachmentName = null;
      _attachmentType = null;
    });
    _controller.sendPrompt(
      text,
      replyTo: replyTo,
      attachmentName: attachmentName,
      attachmentType: attachmentType,
    );
  }

  Future<void> _copyMessage(HermesMessage message) async {
    await Clipboard.setData(ClipboardData(text: message.text));
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(const SnackBar(content: Text('메시지를 복사했습니다.')));
  }

  void _startReply(HermesMessage message) {
    setState(() => _replyToText = message.text);
  }

  Future<void> _pasteFromClipboard() async {
    final data = await Clipboard.getData('text/plain');
    final text = data?.text;
    if (text == null || text.isEmpty) return;
    final selection = _inputController.selection;
    final current = _inputController.text;
    final start = selection.isValid ? selection.start : current.length;
    final end = selection.isValid ? selection.end : current.length;
    _inputController.text = current.replaceRange(start, end, text);
    final offset = start + text.length;
    _inputController.selection = TextSelection.collapsed(offset: offset);
  }

  Future<void> _pickAttachment() async {
    final result = await FilePicker.platform.pickFiles(withData: false);
    final file = result?.files.single;
    if (file == null) return;
    setState(() {
      _attachmentName = file.name;
      _attachmentType = file.extension;
    });
  }

  String _shorten(String text) =>
      text.length <= 60 ? text : '${text.substring(0, 60)}…';
}

class _ComposerChip extends StatelessWidget {
  const _ComposerChip({
    required this.icon,
    required this.label,
    required this.onClear,
  });

  final IconData icon;
  final String label;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, size: 18),
          const SizedBox(width: 8),
          Expanded(
              child: Text(label, maxLines: 2, overflow: TextOverflow.ellipsis)),
          IconButton(
            tooltip: '해제',
            onPressed: onClear,
            icon: const Icon(Icons.close),
          ),
        ],
      ),
    );
  }
}

class _ConnectionBanner extends StatelessWidget {
  const _ConnectionBanner({required this.controller});

  final ChatController controller;

  @override
  Widget build(BuildContext context) {
    final color = controller.connected ? Colors.tealAccent : Colors.amberAccent;
    final text = controller.connected ? '연결됨' : '첫 메시지 전송 시 자동 연결';
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      color: color.withValues(alpha: 0.12),
      child: Text(text),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({
    required this.message,
    required this.onCopy,
    required this.onReply,
    required this.onApprovalChoice,
  });

  final HermesMessage message;
  final ValueChanged<HermesMessage> onCopy;
  final ValueChanged<HermesMessage> onReply;
  final void Function(String approvalId, String choice) onApprovalChoice;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == HermesMessageRole.user;
    final alignment = isUser ? Alignment.centerRight : Alignment.centerLeft;
    final color = switch (message.role) {
      HermesMessageRole.user => Theme.of(context).colorScheme.primaryContainer,
      HermesMessageRole.assistant =>
        Theme.of(context).colorScheme.surfaceContainerHighest,
      HermesMessageRole.tool => Theme.of(context).colorScheme.tertiaryContainer,
      HermesMessageRole.system =>
        Theme.of(context).colorScheme.secondaryContainer,
    };
    final text =
        message.pending && message.text.isEmpty ? '응답 대기 중...' : message.text;
    return Align(
      alignment: alignment,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 340),
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
            color: color, borderRadius: BorderRadius.circular(16)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (message.replyToText != null) ...[
              Text('답장: ${message.replyToText}',
                  maxLines: 2, overflow: TextOverflow.ellipsis),
              const SizedBox(height: 6),
            ],
            if (message.attachmentName != null) ...[
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.attach_file, size: 16),
                  const SizedBox(width: 4),
                  Flexible(child: Text(message.attachmentName!)),
                ],
              ),
              const SizedBox(height: 6),
            ],
            SelectableText(text),
            if (message.approvalId != null && message.choices.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final choice in message.choices)
                    FilledButton.tonal(
                      onPressed: () =>
                          onApprovalChoice(message.approvalId!, choice),
                      child: Text(choice),
                    ),
                ],
              ),
            ],
            const SizedBox(height: 6),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextButton.icon(
                  onPressed: () => onReply(message),
                  icon: const Icon(Icons.reply, size: 16),
                  label: const Text('답장'),
                ),
                TextButton.icon(
                  onPressed: () => onCopy(message),
                  icon: const Icon(Icons.copy, size: 16),
                  label: const Text('복사'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
