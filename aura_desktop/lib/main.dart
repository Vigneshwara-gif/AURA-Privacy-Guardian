import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/theme/aura_theme.dart';
import 'services/api_service.dart';
import 'services/websocket_service.dart';
import 'state/aura_state_provider.dart';
import 'widgets/aura_sidebar.dart';
import 'widgets/aura_topbar.dart';
import 'views/overview_view.dart';
import 'views/scan_view.dart';
import 'views/threat_intel_view.dart';
import 'views/privacy_sentinel_view.dart';
import 'views/process_intel_view.dart';
import 'views/network_intel_view.dart';
import 'views/persistence_view.dart';
import 'views/incidents_view.dart';
import 'views/timeline_view.dart';
import 'views/reports_view.dart';
import 'views/alerts_view.dart';
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
  final TextEditingController _bootstrapCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    // Auto-connect with local agent session if available or prompt operator
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final state = context.read<AuraStateProvider>();
      // Attempt connecting with local default or trigger bootstrap
      _attemptLocalConnect(state);
    });
  }

  void _attemptLocalConnect(AuraStateProvider state) async {
    // Try authenticating or load
    final ok = await state.authenticate('LOCAL_OPERATOR_DEV_SESSION');
    if (!ok && mounted) {
      // Prompt user for bootstrap code
    }
  }

  @override
  void dispose() {
    _bootstrapCtrl.dispose();
    super.dispose();
  }

  static const List<String> sectionTitles = [
    'Executive Overview',
    '16-Category Full PC Security Scan',
    'Threat Intelligence & Explainable AI',
    'Hardware Privacy Sentinel',
    'Process Intelligence & Execution DNA',
    'Network Intelligence & Socket Flow Topology',
    'Auto-Start & Persistence Analysis',
    'Incident Studio & Case Management',
    'Forensic Chronological Security Timeline',
    'Executive & Technical Security Reports',
    'Real-Time Security Alert Center',
    'Agent Policy & System Settings',
  ];

  Widget _buildCurrentView() {
    switch (_selectedIndex) {
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
        return const IncidentsView();
      case 8:
        return const TimelineView();
      case 9:
        return const ReportsView();
      case 10:
        return const AlertsView();
      case 11:
        return const SettingsView();
      default:
        return const OverviewView();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();

    if (!state.isAuthenticated && state.isLoading) {
      return const Scaffold(
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircularProgressIndicator(color: AuraTheme.primaryLight),
              SizedBox(height: 16),
              Text('Connecting to AURA Local Engine...', style: TextStyle(color: AuraTheme.textSecondary)),
            ],
          ),
        ),
      );
    }

    if (!state.isAuthenticated) {
      return Scaffold(
        body: Center(
          child: Container(
            width: 420,
            padding: const EdgeInsets.all(32),
            decoration: BoxDecoration(
              color: AuraTheme.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AuraTheme.border),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AuraTheme.primary.withValues(alpha: 0.15),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.shield_rounded, color: AuraTheme.primaryLight, size: 36),
                ),
                const SizedBox(height: 16),
                const Text('AURA PRIVACY GUARDIAN', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, letterSpacing: 1.5)),
                const SizedBox(height: 6),
                const Text('Enter local agent bootstrap authorization code', style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary)),
                const SizedBox(height: 24),
                TextField(
                  controller: _bootstrapCtrl,
                  decoration: InputDecoration(
                    hintText: 'Bootstrap Code or Session Token...',
                    filled: true,
                    fillColor: AuraTheme.surfaceElevated,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
                  ),
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AuraTheme.primary,
                    foregroundColor: Colors.white,
                    minimumSize: const Size.fromHeight(44),
                  ),
                  onPressed: () {
                    final code = _bootstrapCtrl.text.trim();
                    if (code.isNotEmpty) state.authenticate(code);
                  },
                  child: const Text('AUTHENTICATE & LAUNCH', style: TextStyle(fontWeight: FontWeight.w700)),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      body: Row(
        children: [
          // Navigation Sidebar
          AuraSidebar(
            selectedIndex: _selectedIndex,
            onItemSelected: (i) => setState(() => _selectedIndex = i),
            agentStatus: state.wsStatus == WsConnectionStatus.connected ? 'ONLINE' : 'CONNECTING',
          ),

          // Main Workspace Region
          Expanded(
            child: Column(
              children: [
                // Top App Bar
                AuraTopbar(
                  title: sectionTitles[_selectedIndex],
                  onQuickScan: () => state.runFullSecurityScan(),
                  onAlertsTap: () => setState(() => _selectedIndex = 10),
                  alertCount: state.alerts.where((a) => !a.isAcknowledged).length,
                  isScanning: state.isScanning,
                  connectionState: state.wsStatus == WsConnectionStatus.connected ? 'LIVE' : 'RECONNECTING',
                ),

                // View Content
                Expanded(
                  child: _buildCurrentView(),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
