import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/auth_state.dart';
import '../models/telemetry.dart';
import '../models/security_posture.dart';
import '../models/privacy.dart';
import '../models/scan.dart';
import '../models/process_dna.dart';
import '../models/network_intel.dart';
import '../models/persistence.dart';
import '../models/threat_intel.dart';
import '../models/incident.dart';
import '../models/timeline.dart';
import '../models/alert.dart';
import '../models/report.dart';
import '../models/analytics.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';

class AuraStateProvider extends ChangeNotifier {
  final ApiService apiService;
  final WebSocketService wsService;

  AuthSession? _authSession;
  bool _isAuthenticated = false;
  bool _isLoading = false;
  String? _errorMessage;

  // Real-time & Cached Datasets
  SystemTelemetry? _telemetry;
  SecurityPosture? _posture;
  PrivacySummary? _privacySummary;
  FullScanReport? _latestScan;
  List<SecurityFinding> _findings = [];
  NetworkInvestigation? _network;
  PersistenceAnalysis? _persistence;
  AnomalyExplanation? _aiExplanation;
  ThreatHuntResult? _threatHunts;
  List<IncidentItem> _incidents = [];
  List<TimelineEvent> _timelineEvents = [];
  List<SecurityAlertItem> _alerts = [];
  AnalyticsOverview? _analytics;
  SecurityAuditReport? _latestReport;

  // Live Scan State
  bool _isScanning = false;
  double _scanProgress = 0.0;
  String _scanCurrentCategory = 'Idle';

  // Process DNA Inspection Cache
  ProcessDNAProfile? _selectedProcessDna;
  bool _isLoadingDna = false;

  Timer? _pollingTimer;
  StreamSubscription? _wsSubscription;

  AuraStateProvider({
    required this.apiService,
    required this.wsService,
  }) {
    _initWsListener();
  }

  // Getters
  bool get isAuthenticated => _isAuthenticated;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  AuthSession? get authSession => _authSession;
  WsConnectionStatus get wsStatus => wsService.status;

  SystemTelemetry? get telemetry => _telemetry;
  SecurityPosture? get posture => _posture;
  PrivacySummary? get privacySummary => _privacySummary;
  FullScanReport? get latestScan => _latestScan;
  List<SecurityFinding> get findings => _findings;
  NetworkInvestigation? get network => _network;
  PersistenceAnalysis? get persistence => _persistence;
  AnomalyExplanation? get aiExplanation => _aiExplanation;
  ThreatHuntResult? get threatHunts => _threatHunts;
  List<IncidentItem> get incidents => _incidents;
  List<TimelineEvent> get timelineEvents => _timelineEvents;
  List<SecurityAlertItem> get alerts => _alerts;
  AnalyticsOverview? get analytics => _analytics;
  SecurityAuditReport? get latestReport => _latestReport;

  bool get isScanning => _isScanning;
  double get scanProgress => _scanProgress;
  String get scanCurrentCategory => _scanCurrentCategory;

  ProcessDNAProfile? get selectedProcessDna => _selectedProcessDna;
  bool get isLoadingDna => _isLoadingDna;

  void _initWsListener() {
    _wsSubscription = wsService.eventStream.listen((event) {
      final type = event['type'];
      if (type == 'TELEMETRY_SNAPSHOT' && event['data'] != null) {
        // Updated live snapshot
        notifyListeners();
      } else if (type == 'ALERT' && event['alert'] != null) {
        try {
          final alert = SecurityAlertItem.fromJson(event['alert']);
          _alerts.insert(0, alert);
          notifyListeners();
        } catch (_) {}
      }
    });
  }

  // 1. Authenticate with Bootstrap Code
  Future<bool> authenticate(String bootstrapCode) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _authSession = await apiService.exchangeBootstrap(bootstrapCode);
      _isAuthenticated = true;
      wsService.setSessionToken(_authSession!.sessionId);
      wsService.connect();

      await refreshAllData();
      _startPeriodicPolling();

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  void _startPeriodicPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      if (_isAuthenticated) {
        _pollLiveTelemetry();
      }
    });
  }

  Future<void> _pollLiveTelemetry() async {
    try {
      _telemetry = await apiService.getSystemInfo();
      _privacySummary = await apiService.getPrivacySummary();
      notifyListeners();
    } catch (_) {}
  }

  // Refresh all state
  Future<void> refreshAllData() async {
    if (!_isAuthenticated) return;
    try {
      try { _telemetry = await apiService.getSystemInfo(); } catch (_) {}
      try { _posture = await apiService.getSecurityPosture(); } catch (_) {}
      try { _privacySummary = await apiService.getPrivacySummary(); } catch (_) {}
      try { _findings = await apiService.getFindings(); } catch (_) {}
      try { _network = await apiService.investigateNetwork(); } catch (_) {}
      try { _persistence = await apiService.analyzePersistence(); } catch (_) {}
      try { _aiExplanation = await apiService.getAiExplanation(); } catch (_) {}
      try { _incidents = await apiService.getIncidents(); } catch (_) {}
      try { _timelineEvents = await apiService.getTimeline(); } catch (_) {}
      try { _alerts = await apiService.getAlerts(); } catch (_) {}
      try { _analytics = await apiService.getAnalyticsOverview(); } catch (_) {}
      try { _latestScan = await apiService.getLatestScan(); } catch (_) {}
      notifyListeners();
    } catch (e) {
      debugPrint('Error refreshing AURA state: $e');
    }
  }

  // 2. Trigger Full Security Scan
  Future<FullScanReport?> runFullSecurityScan() async {
    if (_isScanning) return null;
    _isScanning = true;
    _scanProgress = 0.1;
    _scanCurrentCategory = 'Initializing Checkpoints...';
    notifyListeners();

    try {
      // Simulate stepped progress indicator while backend scan executes
      Timer? stepTimer;
      final categories = [
        'Hardware Security Architecture',
        'Kernel & Subsystem Protections',
        'Antivirus Real-Time Defense',
        'Windows Defender Firewall',
        'Authentication & Credential Isolation',
        'System Integrity & Secure Boot',
        'Hardware Privacy Sentinels',
      ];
      int step = 0;
      stepTimer = Timer.periodic(const Duration(milliseconds: 350), (_) {
        if (step < categories.length) {
          _scanCurrentCategory = categories[step];
          _scanProgress = (step + 1) / (categories.length + 1);
          notifyListeners();
          step++;
        }
      });

      final report = await apiService.triggerFullScan();
      stepTimer.cancel();

      _latestScan = report;
      _findings = report.findings;
      _scanProgress = 1.0;
      _scanCurrentCategory = 'Scan Complete';
      _isScanning = false;

      await refreshAllData();
      notifyListeners();
      return report;
    } catch (e) {
      _isScanning = false;
      _errorMessage = 'Scan failed: $e';
      notifyListeners();
      return null;
    }
  }

  // 3. Inspect Process DNA
  Future<ProcessDNAProfile?> inspectProcessDna(int pid) async {
    _isLoadingDna = true;
    _selectedProcessDna = null;
    notifyListeners();

    try {
      _selectedProcessDna = await apiService.getProcessDna(pid);
      _isLoadingDna = false;
      notifyListeners();
      return _selectedProcessDna;
    } catch (e) {
      _isLoadingDna = false;
      notifyListeners();
      return null;
    }
  }

  // 4. Safe Stop Process
  Future<bool> terminateProcess(int pid) async {
    try {
      final res = await apiService.terminateProcess(pid);
      if (res['success'] == true) {
        await refreshAllData();
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  // 5. Open Windows Settings Shortcut
  Future<void> openShortcut(String shortcutType) async {
    try {
      await apiService.openShortcut(shortcutType);
    } catch (_) {}
  }

  // 6. Threat Hunting
  Future<void> runThreatHunts() async {
    _isLoading = true;
    notifyListeners();
    try {
      _threatHunts = await apiService.runThreatHunts();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();
    }
  }

  // 7. Update Incident State
  Future<bool> updateIncidentState(String incidentId, String newState, {String note = ''}) async {
    try {
      final ok = await apiService.updateIncidentState(incidentId, newState, note: note);
      if (ok) {
        _incidents = await apiService.getIncidents();
        notifyListeners();
      }
      return ok;
    } catch (_) {
      return false;
    }
  }

  // 8. Acknowledge Alert
  Future<bool> acknowledgeAlert(String alertId) async {
    try {
      final ok = await apiService.acknowledgeAlert(alertId);
      if (ok) {
        _alerts = await apiService.getAlerts();
        notifyListeners();
      }
      return ok;
    } catch (_) {
      return false;
    }
  }

  // 9. Generate Report
  Future<SecurityAuditReport?> generateReport() async {
    _isLoading = true;
    notifyListeners();
    try {
      _latestReport = await apiService.generateReport();
      _isLoading = false;
      notifyListeners();
      return _latestReport;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return null;
    }
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    _wsSubscription?.cancel();
    wsService.dispose();
    super.dispose();
  }
}
