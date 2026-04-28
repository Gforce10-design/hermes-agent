enum HermesMessageRole { user, assistant, system, tool }

enum HermesJobStatus { accepted, progress, completed, failed }

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
    this.jobStatus,
    this.jobId,
    this.jobTitle,
    this.jobProgress,
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
  final HermesJobStatus? jobStatus;
  final String? jobId;
  final String? jobTitle;
  final int? jobProgress;

  bool get isJob => jobStatus != null;

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
    HermesJobStatus? jobStatus,
    String? jobId,
    String? jobTitle,
    int? jobProgress,
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
      jobStatus: jobStatus ?? this.jobStatus,
      jobId: jobId ?? this.jobId,
      jobTitle: jobTitle ?? this.jobTitle,
      jobProgress: jobProgress ?? this.jobProgress,
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
        if (jobStatus != null) 'jobStatus': jobStatus!.name,
        if (jobId != null) 'jobId': jobId,
        if (jobTitle != null) 'jobTitle': jobTitle,
        if (jobProgress != null) 'jobProgress': jobProgress,
      };

  static HermesMessage fromJson(Map<String, dynamic> json) {
    final roleName = json['role']?.toString() ?? 'system';
    final role = HermesMessageRole.values.firstWhere(
      (value) => value.name == roleName,
      orElse: () => HermesMessageRole.system,
    );
    final jobStatusName = json['jobStatus']?.toString();
    final jobStatus = jobStatusName == null
        ? null
        : HermesJobStatus.values.cast<HermesJobStatus?>().firstWhere(
              (value) => value?.name == jobStatusName,
              orElse: () => null,
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
      jobStatus: jobStatus,
      jobId: json['jobId']?.toString(),
      jobTitle: json['jobTitle']?.toString(),
      jobProgress: _parseInt(json['jobProgress']),
    );
  }

  static int? _parseInt(Object? value) {
    if (value is int) return value;
    if (value is num) return value.round();
    return int.tryParse(value?.toString() ?? '');
  }
}
