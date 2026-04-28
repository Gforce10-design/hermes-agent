import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'features/chat/chat_screen.dart';
import 'features/settings/settings_screen.dart';
import 'features/update/update_service.dart';
import 'services/hermes_rest_client.dart';
import 'services/hermes_ws_client.dart';

class HermesMobileApp extends StatefulWidget {
  const HermesMobileApp({super.key, this.statusService = const HermesRestClient()});

  final HermesStatusService statusService;

  @override
  State<HermesMobileApp> createState() => _HermesMobileAppState();
}

class _HermesMobileAppState extends State<HermesMobileApp> {
  static const _serverUrlKey = 'serverUrl';
  static const _sessionTokenKey = 'sessionToken';
  static const _accessClientIdKey = 'cloudflareAccessClientId';
  static const _accessClientSecretKey = 'cloudflareAccessClientSecret';

  int _index = 0;
  String _serverUrl = 'https://hrs.alpha-mates.com/console';
  String _sessionToken = '';
  String _cloudflareAccessClientId = '';
  String _cloudflareAccessClientSecret = '';
  bool _loaded = false;
  AppUpdateInfo? _lastUpdateInfo;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _serverUrl = prefs.getString(_serverUrlKey) ?? _serverUrl;
      _sessionToken = prefs.getString(_sessionTokenKey) ?? _sessionToken;
      _cloudflareAccessClientId =
          prefs.getString(_accessClientIdKey) ?? _cloudflareAccessClientId;
      _cloudflareAccessClientSecret = prefs.getString(_accessClientSecretKey) ??
          _cloudflareAccessClientSecret;
      _loaded = true;
    });
  }

  Future<void> _saveSettings(
    String serverUrl,
    String sessionToken,
    String accessClientId,
    String accessClientSecret,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_serverUrlKey, serverUrl);
    await prefs.setString(_sessionTokenKey, sessionToken);
    await prefs.setString(_accessClientIdKey, accessClientId);
    await prefs.setString(_accessClientSecretKey, accessClientSecret);
    if (!mounted) return;
    setState(() {
      _serverUrl = serverUrl;
      _sessionToken = sessionToken;
      _cloudflareAccessClientId = accessClientId;
      _cloudflareAccessClientSecret = accessClientSecret;
    });
  }

  Future<String> _testConnection(
    String serverUrl,
    String accessClientId,
    String accessClientSecret,
  ) async {
    final diagnostics = HermesWsClient.buildAccessDiagnostics(
      serverUrl: serverUrl,
      cloudflareAccessClientId: accessClientId,
      cloudflareAccessClientSecret: accessClientSecret,
    );
    final diagnosticMessage = '진단: ${diagnostics.safeSummary}';
    try {
      final accessHeaders = HermesWsClient.buildAccessHeaders(
        cloudflareAccessClientId: accessClientId,
        cloudflareAccessClientSecret: accessClientSecret,
      );
      if (accessHeaders.isEmpty) {
        return '$diagnosticMessage\n연결 테스트 실패: Cloudflare Access Client ID/Secret이 모두 필요합니다.';
      }
      final wsUrl = await HermesWsClient.fetchMobileWsUrl(
        serverUrl: serverUrl,
        accessHeaders: accessHeaders,
      );
      return wsUrl.isEmpty
          ? '$diagnosticMessage\n연결 정보를 확인하지 못했습니다.'
          : '$diagnosticMessage\n연결 테스트 성공';
    } catch (error) {
      return '$diagnosticMessage\n연결 테스트 실패: $error';
    }
  }

  Future<String> _checkUpdate(
    String serverUrl,
    String accessClientId,
    String accessClientSecret,
  ) async {
    try {
      final result = await AppUpdateService.checkLatest(
        serverUrl: serverUrl,
        cloudflareAccessClientId: accessClientId,
        cloudflareAccessClientSecret: accessClientSecret,
      );
      if (!mounted) return result.userMessage;
      setState(() {
        _lastUpdateInfo = result.updateAvailable ? result.latest : null;
      });
      return result.userMessage;
    } catch (error) {
      return '업데이트 확인 실패: $error';
    }
  }

  Future<String> _openUpdate() async {
    final info = _lastUpdateInfo;
    if (info == null) return '설치할 업데이트가 없습니다.';
    try {
      await AppUpdateService.openUpdate(info);
      return '업데이트 파일을 열었습니다. Android 설치 화면에서 “업데이트”를 선택하세요.';
    } catch (error) {
      return '업데이트 열기 실패: $error';
    }
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      _HomeScreen(
        serverUrl: _serverUrl,
        accessConfigured: _cloudflareAccessClientId.isNotEmpty &&
            _cloudflareAccessClientSecret.isNotEmpty,
        loaded: _loaded,
      ),
      ChatScreen(
        serverUrl: _serverUrl,
        sessionToken: _sessionToken,
        cloudflareAccessClientId: _cloudflareAccessClientId,
        cloudflareAccessClientSecret: _cloudflareAccessClientSecret,
      ),
      const _AgentsScreen(),
      StatusScreen(
        serverUrl: _serverUrl,
        sessionToken: _sessionToken,
        cloudflareAccessClientId: _cloudflareAccessClientId,
        cloudflareAccessClientSecret: _cloudflareAccessClientSecret,
        loaded: _loaded,
        active: _index == 3,
        statusService: widget.statusService,
      ),
      SettingsScreen(
        serverUrl: _serverUrl,
        sessionToken: _sessionToken,
        cloudflareAccessClientId: _cloudflareAccessClientId,
        cloudflareAccessClientSecret: _cloudflareAccessClientSecret,
        onChanged: _saveSettings,
        onTestConnection: _testConnection,
        onCheckUpdate: _checkUpdate,
        onOpenUpdate: _openUpdate,
      ),
    ];

    return MaterialApp(
      title: 'Hermes Mobile',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF14B8A6),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: Scaffold(
        appBar: AppBar(title: const Text('Hermes Mobile')),
        body: IndexedStack(index: _index, children: pages),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (value) => setState(() => _index = value),
          destinations: const [
            NavigationDestination(
                icon: Icon(Icons.dashboard_outlined), label: '홈'),
            NavigationDestination(
                icon: Icon(Icons.chat_bubble_outline), label: '채팅'),
            NavigationDestination(
                icon: Icon(Icons.hub_outlined), label: '멀티에이전트'),
            NavigationDestination(
                icon: Icon(Icons.monitor_heart_outlined), label: '상태'),
            NavigationDestination(
                icon: Icon(Icons.settings_outlined), label: '설정'),
          ],
        ),
      ),
    );
  }
}

class _HomeScreen extends StatelessWidget {
  const _HomeScreen({
    required this.serverUrl,
    required this.accessConfigured,
    required this.loaded,
  });

  final String serverUrl;
  final bool accessConfigured;
  final bool loaded;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('오늘의 Hermes', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 12),
        _InfoCard(
          title: '연결 상태',
          body: loaded
              ? '서버: $serverUrl\nCloudflare Access: ${accessConfigured ? '설정됨' : '미설정'}'
              : '설정을 불러오는 중입니다.',
          icon: Icons.cloud_done_outlined,
        ),
        const SizedBox(height: 12),
        const _InfoCard(
          title: '빠른 작업',
          body: '채팅 시작 · 연결 테스트 · 인프라 상태 확인',
          icon: Icons.flash_on_outlined,
        ),
        const SizedBox(height: 12),
        const _InfoCard(
          title: 'Telegram 대체 준비',
          body: '대화, 승인, 장애 알림, AlphaMate 운영 화면을 이 앱 안으로 확장할 예정입니다.',
          icon: Icons.apps_outlined,
        ),
      ],
    );
  }
}

class _AgentsScreen extends StatelessWidget {
  const _AgentsScreen();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: const [
        Text('멀티에이전트',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.w600)),
        SizedBox(height: 12),
        _InfoCard(
          title: 'Codex OAuth',
          body: '주 응답 엔진 · API 키 비용 없이 OAuth 기반으로 먼저 응답합니다.',
          icon: Icons.bolt_outlined,
        ),
        SizedBox(height: 12),
        _InfoCard(
          title: 'Claude CLI Opus 4.7',
          body: '폴백 엔진 · Codex 지연, 빈 응답, 오류 시 고품질 복구 응답을 담당합니다.',
          icon: Icons.psychology_alt_outlined,
        ),
        SizedBox(height: 12),
        _InfoCard(
          title: 'Hermes 운영',
          body: '콘솔, 크론, 게이트웨이, 모바일 연결 상태를 관리하는 운영 에이전트입니다.',
          icon: Icons.settings_suggest_outlined,
        ),
        SizedBox(height: 12),
        _InfoCard(
          title: 'AlphaMate 운영',
          body: 'Agent, Dashboard, Telebot, G3 운영 상태를 확인하고 조치하는 에이전트입니다.',
          icon: Icons.auto_graph_outlined,
        ),
      ],
    );
  }
}

class StatusScreen extends StatefulWidget {
  const StatusScreen({
    super.key,
    required this.serverUrl,
    required this.sessionToken,
    required this.cloudflareAccessClientId,
    required this.cloudflareAccessClientSecret,
    required this.loaded,
    required this.active,
    this.statusService = const HermesRestClient(),
  });

  final String serverUrl;
  final String sessionToken;
  final String cloudflareAccessClientId;
  final String cloudflareAccessClientSecret;
  final bool loaded;
  final bool active;
  final HermesStatusService statusService;

  @override
  State<StatusScreen> createState() => _StatusScreenState();
}

class _StatusScreenState extends State<StatusScreen> {
  MobileStatusSnapshot? _snapshot;
  String? _error;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _fetchIfReady();
  }

  @override
  void didUpdateWidget(covariant StatusScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    final becameActive = widget.active && !oldWidget.active;
    final settingsChanged = widget.serverUrl != oldWidget.serverUrl ||
        widget.sessionToken != oldWidget.sessionToken ||
        widget.cloudflareAccessClientId != oldWidget.cloudflareAccessClientId ||
        widget.cloudflareAccessClientSecret !=
            oldWidget.cloudflareAccessClientSecret;
    if (becameActive || (widget.active && settingsChanged)) {
      _fetchIfReady();
    }
  }

  Future<void> _fetchIfReady() async {
    if (!widget.loaded || !widget.active || _loading) return;
    await _refresh();
  }

  Future<void> _refresh() async {
    if (!widget.loaded) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final snapshot = await widget.statusService.fetchStatus(
        serverUrl: widget.serverUrl,
        sessionToken: widget.sessionToken,
        cloudflareAccessClientId: widget.cloudflareAccessClientId,
        cloudflareAccessClientSecret: widget.cloudflareAccessClientSecret,
      );
      if (!mounted) return;
      setState(() {
        _snapshot = snapshot;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = '$error';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final snapshot = _snapshot;
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              Expanded(
                child: Text('운영 상태',
                    style: Theme.of(context).textTheme.headlineSmall),
              ),
              IconButton(
                tooltip: '새로고침',
                onPressed: _loading ? null : _refresh,
                icon: const Icon(Icons.refresh),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (!widget.loaded)
            const _InfoCard(
              title: '상태 불러오는 중',
              body: '저장된 연결 설정을 읽고 있습니다.',
              icon: Icons.hourglass_empty_outlined,
            )
          else if (_loading && snapshot == null)
            const _InfoCard(
              title: '상태 불러오는 중',
              body: 'Hermes 모바일 상태 API에 연결하고 있습니다.',
              icon: Icons.sync_outlined,
            )
          else if (_error != null)
            _InfoCard(
              title: '상태 조회 실패',
              body: '서버 URL, 세션 토큰 또는 Cloudflare Access 설정을 확인해 주세요.\n$_error',
              icon: Icons.error_outline,
            )
          else if (snapshot == null)
            const _InfoCard(
              title: '상태 대기 중',
              body: '새로고침을 눌러 Hermes 상태를 확인하세요.',
              icon: Icons.monitor_heart_outlined,
            )
          else ...[
            _InfoCard(
              title: 'Hermes',
              body:
                  '${_stateLabel(snapshot.hermes.state)} · ${snapshot.hermes.service}\n${snapshot.hermes.detail}',
              icon: Icons.dns_outlined,
            ),
            const SizedBox(height: 12),
            _InfoCard(
              title: '모바일 API',
              body:
                  '${_stateLabel(snapshot.mobileApi.state)} · 인증: ${_authLabel(snapshot.mobileApi.auth)}\n${snapshot.mobileApi.detail}',
              icon: Icons.phone_android_outlined,
            ),
            const SizedBox(height: 12),
            _InfoCard(
              title: 'AlphaMate',
              body:
                  '${snapshot.alphaMate.summary}\n${snapshot.alphaMate.detail}',
              icon: Icons.auto_graph_outlined,
            ),
            const SizedBox(height: 12),
            _NotificationCard(notifications: snapshot.notifications),
            const SizedBox(height: 12),
            _ReadOnlyActionsCard(actions: snapshot.readOnlyActions),
            const SizedBox(height: 12),
            _RecentSessionsCard(sessions: snapshot.recentSessions),
            const SizedBox(height: 8),
            Text('갱신 시각: ${snapshot.generatedAt}',
                style: Theme.of(context).textTheme.bodySmall),
          ],
        ],
      ),
    );
  }

  static String _stateLabel(String state) {
    return switch (state) {
      'running' => '실행 중',
      'online' => '온라인',
      'idle' => '대기',
      'stopped' => '중지됨',
      'placeholder' => '요약',
      _ => state,
    };
  }

  static String _authLabel(String auth) {
    return switch (auth) {
      'dashboard_session' => '세션 토큰',
      'cloudflare_access_service_token' => 'Access 서비스 토큰',
      'cloudflare_access_assertion' => 'Access 로그인',
      _ => auth,
    };
  }
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({required this.notifications});

  final List<HermesNotification> notifications;

  @override
  Widget build(BuildContext context) {
    final body = notifications.isEmpty
        ? '현재 표시할 알림이 없습니다.'
        : notifications
            .map((item) => '• ${item.title}: ${item.message}')
            .join('\n');
    return _InfoCard(
      title: '알림함',
      body: body,
      icon: Icons.notifications_active_outlined,
    );
  }
}

class _ReadOnlyActionsCard extends StatelessWidget {
  const _ReadOnlyActionsCard({required this.actions});

  final List<HermesReadOnlyAction> actions;

  @override
  Widget build(BuildContext context) {
    final body = actions.isEmpty
        ? '현재 실행 가능한 읽기 전용 액션이 없습니다.'
        : actions
            .map((item) =>
                '• ${item.title}: ${item.description} (${item.method} ${item.path})')
            .join('\n');
    return _InfoCard(
      title: '읽기 전용 액션',
      body: body,
      icon: Icons.fact_check_outlined,
    );
  }
}

class _RecentSessionsCard extends StatelessWidget {
  const _RecentSessionsCard({required this.sessions});

  final List<HermesRecentSession> sessions;

  @override
  Widget build(BuildContext context) {
    final body = sessions.isEmpty
        ? '최근 세션이 없습니다.'
        : sessions
            .map((item) =>
                '• ${item.label}${item.isActive ? ' · 활성' : ''}')
            .join('\n');
    return _InfoCard(
      title: '최근 세션',
      body: body,
      icon: Icons.history_outlined,
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard(
      {required this.title, required this.body, required this.icon});

  final String title;
  final String body;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 28),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 6),
                  Text(body),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
