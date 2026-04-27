enum HermesMessageRole { user, assistant, system, tool }

class HermesMessage {
  const HermesMessage({
    required this.role,
    required this.text,
    this.pending = false,
  });

  final HermesMessageRole role;
  final String text;
  final bool pending;

  HermesMessage copyWith({
    HermesMessageRole? role,
    String? text,
    bool? pending,
  }) {
    return HermesMessage(
      role: role ?? this.role,
      text: text ?? this.text,
      pending: pending ?? this.pending,
    );
  }
}
