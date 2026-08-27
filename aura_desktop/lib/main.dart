import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/theme/aura_theme.dart';
import 'services/api_service.dart';
import 'services/websocket_service.dart';
import 'state/aura_state_provider.dart';
import 'widgets/aura_sidebar.dart';
import 'widgets/aura_topbar.dart';
import 'views/onboarding_view.dart';
import 'views/overview_view.dart';
import 'views/scan_view.dart';
import 'views/threat_intel_view.dart';
import 'views/privacy_sentinel_view.dart';
import 'views/process_intel_view.dart';
import 'views/network_intel_view.dart';
import 'views/persistence_view.dart';
import 'views/security_events_view.dart';
import 'views/incidents_view.dart';
import 'views/timeline_view.dart';
import 'views/reports_view.dart';
import 'views/settings_view.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final apiService = ApiService();
  final wsService = WebSocketService();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (_) => AuraStateProvider(
            apiService: apiService,
            wsService: wsService,
          ),
        ),
      ],
      child: const AuraDesktopApp(),
    ),
  );
}

class AuraDesktopApp extends StatelessWidget {
  const AuraDesktopApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AURA — Privacy Guardian',
      debugShowCheckedModeBanner: false,
      theme: AuraTheme.darkTheme,
      home: const AuraMainShell(),
    );
  }
}

class AuraMainShell extends StatefulWidget {
  const AuraMainShell({super.key});

  @override
  State<AuraMainShell> createState() => _AuraMainShellState();
}

class _AuraMainShellState extends State<AuraMainShell> {
  bool _isOnboardingActive = false;
  bool _isInitialLaunch = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final state = context.read<AuraStateProvider>();
      _attemptLocalConnect(state);
    });
  }

  void _attemptLocalConnect(AuraStateProvider state) async {
    final ok = await state.authenticate();
    if (mounted) {
      setState(() {
        _isInitialLaunch = false;
        if (!ok) {
          _isOnboardingActive = true;
        }
      });
    }
  }

  static const List<String> sectionTitles = [
    'AURA Command Center',
    'AURA Full Security Assessment',
    'Threat Intelligence & Explainable AI',
    'Hardware Privacy Sentinel',
    'Process Intelligence & Execution DNA',
    'Network Intelligence & Socket Flow Topology',
    'Startup & Background Services Analysis',
    'Real-Time Security Event Center',
    'Incident Studio & Case Management',
    'Forensic Chronological Security Timeline',
    'Executive & Technical Security Reports',
    'Agent Policy & System Settings',
  ];

  Widget _buildCurrentView(int index) {
    switch (index) {
      case 0:
        return const OverviewView();
      case 1:
        return const ScanView();
      case 2:
        return const ThreatIntelView();
      case 3:
        return const PrivacySentinelView();
      case 4:
        return const ProcessIntelView();
      case 5:
        return const NetworkIntelView();
      case 6:
        return const PersistenceView();
      case 7:
        return const SecurityEventsView();
      case 8:
        return const IncidentsView();
      case 9:
        return const TimelineView();
      case 10:
        return const ReportsView();
      case 11:
        return SettingsView(
          onReopenOnboarding: () => setState(() => _isOnboardingActive = true),
        );
      default:
        return const OverviewView();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();

    if (_isInitialLaunch && state.sessionState == LocalSessionState.connecting) {
      return _buildLaunchScreen(state);
    }

    if (_isOnboardingActive || !state.isAuthenticated) {
      return OnboardingView(
        onFinish: () {
          setState(() {
            _isOnboardingActive = false;
          });
        },
      );
    }

    final currentIndex = state.navigationIndex;

    return Scaffold(
      body: Row(
        children: [
          // Navigation Sidebar
          AuraSidebar(
            selectedIndex: currentIndex,
            onItemSelected: (i) => state.navigateTo(i),
            agentStatus: state.isAuthenticated ? 'ONLINE' : 'OFFLINE',
          ),

          // Main Screen Content Area
          Expanded(
            child: Column(
              children: [
                // Top Action Bar
                AuraTopbar(
                  title: sectionTitles[currentIndex < sectionTitles.length ? currentIndex : 0],
                  isScanning: state.isScanning,
                  alertCount: state.alerts.where((a) => !a.isAcknowledged).length,
                  connectionState: state.isAuthenticated ? 'LIVE' : 'DISCONNECTED',
                  onQuickScan: () {
                    state.navigateTo(1);
                    state.runFullSecurityScan();
                  },
                  onAlertsTap: () {
                    state.navigateTo(7);
                  },
                ),

                // Active Feature View
                Expanded(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 200),
                    child: _buildCurrentView(currentIndex),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // PHASE 3: RESTRAINED CINEMATIC LAUNCH SCREEN
  // -------------------------------------------------------------
  Widget _buildLaunchScreen(AuraStateProvider state) {
    return Scaffold(
      backgroundColor: AuraTheme.background,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: AuraTheme.primary.withValues(alpha: 0.15),
                shape: BoxShape.circle,
                border: Border.all(color: AuraTheme.primaryLight.withValues(alpha: 0.4), width: 1.5),
              ),
              child: const Icon(Icons.shield_rounded, color: AuraTheme.primaryLight, size: 40),
            ),
            const SizedBox(height: 24),
            const Text(
              'AURA',
              style: TextStyle(
                fontSize: 26,
                fontWeight: FontWeight.w900,
                letterSpacing: 4.0,
                color: AuraTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Privacy Guardian',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: AuraTheme.textSecondary,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: 32),
            const SizedBox(
              width: 140,
              child: LinearProgressIndicator(
                minHeight: 3,
                backgroundColor: AuraTheme.border,
                valueColor: AlwaysStoppedAnimation<Color>(AuraTheme.primaryLight),
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Connecting to local security engine on 127.0.0.1:8787...',
              style: TextStyle(fontSize: 11, color: AuraTheme.textSecondary, fontFamily: 'monospace'),
            ),
          ],
        ),
      ),
    );
  }
}
