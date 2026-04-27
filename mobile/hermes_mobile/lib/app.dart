import 'package:flutter/material.dart';

import 'features/chat/chat_screen.dart';
import 'features/settings/settings_screen.dart';

class HermesMobileApp extends StatefulWidget {
  const HermesMobileApp({super.key});

  @override
  State<HermesMobileApp> createState() => _HermesMobileAppState();
}

class _HermesMobileAppState extends State<HermesMobileApp> {
  int _index = 0;
  String _serverUrl = 'https://hrs.alpha-mates.com/console';
  String _sessionToken = '';

  @override
  Widget build(BuildContext context) {
    final pages = [
      ChatScreen(serverUrl: _serverUrl, sessionToken: _sessionToken),
      SettingsScreen(
        serverUrl: _serverUrl,
        sessionToken: _sessionToken,
        onChanged: (serverUrl, sessionToken) {
          setState(() {
            _serverUrl = serverUrl;
            _sessionToken = sessionToken;
          });
        },
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
        body: pages[_index],
        bottomNavigationBar: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (value) => setState(() => _index = value),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.chat_bubble_outline), label: '채팅'),
            NavigationDestination(icon: Icon(Icons.settings_outlined), label: '설정'),
          ],
        ),
      ),
    );
  }
}
