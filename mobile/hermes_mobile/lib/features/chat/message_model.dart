enum HermesMessageRole { user, assistant, system, tool }

class HermesMessage {
  const HermesMessage({
    required this.role,
    required this.text,
    this.pending = false,
    this.id,
    this.createdAt,
    this.replyToText,
    this.attachmentName,
    this.attachmentType,
    this.approvalId,
    this.choices = const [],
  });

  final HermesMessageRole role;
  final String text;
  final bool pending;
  final String? id;
  final DateTime? createdAt;
  final String? replyToText;
  final String? attachmentName;
  final String? attachmentType;
  final String? approvalId;
  final List<String> choices;

  HermesMessage copyWith({
    HermesMessageRole? role,
    String? text,
    bool? pending,
    String? id,
    DateTime? createdAt,
    String? replyToText,
    String? attachmentName,
    String? attachmentType,
    String? approvalId,
    List<String>? choices,
  }) {
    return HermesMessage(
      role: role ?? this.role,
      text: text ?? this.text,
      pending: pending ?? this.pending,
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      replyToText: replyToText ?? this.replyToText,
      attachmentName: attachmentName ?? this.attachmentName,
      attachmentType: attachmentType ?? this.attachmentType,
      approvalId: approvalId ?? this.approvalId,
      choices: choices ?? this.choices,
    );
  }

  Map<String, dynamic> toJson() => {
        'role': role.name,
        'text': text,
        'pending': pending,
        if (id != null) 'id': id,
        if (createdAt != null) 'createdAt': createdAt!.toIso8601String(),
        if (replyToText != null) 'replyToText': replyToText,
        if (attachmentName != null) 'attachmentName': attachmentName,
        if (attachmentType != null) 'attachmentType': attachmentType,
        if (approvalId != null) 'approvalId': approvalId,
        if (choices.isNotEmpty) 'choices': choices,
      };

  static HermesMessage fromJson(Map<String, dynamic> json) {
    final roleName = json['role']?.toString() ?? 'system';
    final role = HermesMessageRole.values.firstWhere(
      (value) => value.name == roleName,
      orElse: () => HermesMessageRole.system,
    );
    return HermesMessage(
      role: role,
      text: json['text']?.toString() ?? '',
      pending: json['pending'] == true,
      id: json['id']?.toString(),
      createdAt: DateTime.tryParse(json['createdAt']?.toString() ?? ''),
      replyToText: json['replyToText']?.toString(),
      attachmentName: json['attachmentName']?.toString(),
      attachmentType: json['attachmentType']?.toString(),
      approvalId: json['approvalId']?.toString(),
      choices: (json['choices'] is List)
          ? (json['choices'] as List).map((item) => item.toString()).toList()
          : const [],
    );
  }
}
