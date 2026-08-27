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
  int _selectedIndex = 0;
  bool _isOnboardingActive = false;

  @override
  void initState() {
    super.initState();
    // Auto-connect with local agent session
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final state = context.read<AuraStateProvider>();
      _attemptLocalConnect(state);
    });
  }

  void _attemptLocalConnect(AuraStateProvider state) async {
    final ok = await state.authenticate('LOCAL_OPERATOR_DEV_SESSION');
    if (!ok && mounted) {
      setState(() {
        _isOnboardingActive = true;
      });
    }
  }

  static const List<String> sectionTitles = [
    'AURA Command Center',
    '16-Category Full PC Security Check',
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

  Widget _buildCurrentView() {
    switch (_selectedIndex) {
      case 0:
        return OverviewView(
          onNavigateToScan: () => setState(() => _selectedIndex = 1),
          onNavigateToPrivacy: () => setState(() => _selectedIndex = 3),
          onNavigateToProcesses: () => setState(() => _selectedIndex = 4),
        );
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

    if (_isOnboardingActive || !state.isAuthenticated) {
      return OnboardingView(
        onFinish: () {
          setState(() {
            _isOnboardingActive = false;
          });
        },
      );
    }

    return Scaffold(
      body: Row(
        children: [
          // Navigation Sidebar
          AuraSidebar(
            selectedIndex: _selectedIndex,
            onItemSelected: (i) => setState(() => _selectedIndex = i),
            agentStatus: state.isAuthenticated ? 'ONLINE' : 'OFFLINE',
          ),

          // Main Screen Content Area
          Expanded(
            child: Column(
              children: [
                // Top Action Bar
                AuraTopbar(
                  title: sectionTitles[_selectedIndex],
                  isScanning: state.isScanning,
                  alertCount: state.alerts.where((a) => !a.isAcknowledged).length,
                  connectionState: state.isAuthenticated ? 'LIVE' : 'DISCONNECTED',
                  onQuickScan: () {
                    setState(() => _selectedIndex = 1);
                    state.runFullSecurityScan();
                  },
                  onAlertsTap: () {
                    setState(() => _selectedIndex = 7); // Navigate to Security Events
                  },
                ),

                // Active Feature View
                Expanded(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 200),
                    child: _buildCurrentView(),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
