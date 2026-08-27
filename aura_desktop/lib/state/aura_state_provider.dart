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

enum LocalSessionState {
  disconnected,
  connecting,
  authenticating,
  ready,
  failed,
}

class SystemStoryEvent {
  final DateTime timestamp;
  final String category; // PROCESS, NETWORK, PRIVACY, BEHAVIOUR, SECURITY, FINDING
  final String title;
  final String detail;
  final String severity; // INFO, LOW, MEDIUM, HIGH, CRITICAL
  final int? pid;
  final String? remoteIp;

  SystemStoryEvent({
    required this.timestamp,
    required this.category,
    required this.title,
    required this.detail,
    this.severity = 'INFO',
    this.pid,
    this.remoteIp,
  });
}

class AuraStateProvider extends ChangeNotifier {
  final ApiService apiService;
  final WebSocketService wsService;

  AuthSession? _authSession;
  bool _isAuthenticated = false;
  bool _isLoading = false;
  String? _errorMessage;
  String? _lastTechnicalError;
  LocalSessionState _sessionState = LocalSessionState.disconnected;

  // Active Navigation & Cross-Drill targets
  int _navigationIndex = 0;
  int? _targetProcessPid;
  String? _targetNetworkIp;
  String? _targetFindingId;

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

  // Live System Story Stream
  final List<SystemStoryEvent> _liveSystemStory = [];

  // Live Scan State
  bool _isScanning = false;
  double _scanProgress = 0.0;
  String _scanCurrentCategory = 'Idle';

  // Process DNA Inspection Cache
  ProcessDNAProfile? _selectedProcessDna;
  bool _isLoadingDna = false;

  Timer? _pollingTimer;
  StreamSubscription? _wsSubscription;
  bool _isAutoRecovering = false;

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
  String? get lastTechnicalError => _lastTechnicalError;
  LocalSessionState get sessionState => _sessionState;
  AuthSession? get authSession => _authSession;
  WsConnectionStatus get wsStatus => wsService.status;

  int get navigationIndex => _navigationIndex;
  int? get targetProcessPid => _targetProcessPid;
  String? get targetNetworkIp => _targetNetworkIp;
  String? get targetFindingId => _targetFindingId;

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
  List<SystemStoryEvent> get liveSystemStory => List.unmodifiable(_liveSystemStory);

  bool get isScanning => _isScanning;
  double get scanProgress => _scanProgress;
  String get scanCurrentCategory => _scanCurrentCategory;

  ProcessDNAProfile? get selectedProcessDna => _selectedProcessDna;
  bool get isLoadingDna => _isLoadingDna;

  String get technicalDiagnostics {
    final sb = StringBuffer();
    sb.writeln('Engine Endpoint: ${apiService.baseUrl}');
    sb.writeln('Authenticated: $_isAuthenticated');
    sb.writeln('Session State: $_sessionState');
    sb.writeln('Session ID: ${_authSession?.sessionId.substring(0, 8) ?? "None"}...');
    sb.writeln('WebSocket Status: $wsStatus');
    if (_lastTechnicalError != null) {
      sb.writeln('Last Diagnostic Fault: $_lastTechnicalError');
    }
    return sb.toString();
  }

  String get machineReadinessSummary {
    int activeSensors = 0;
    if (_telemetry != null) activeSensors += 3;
    if (_posture != null) activeSensors += 2;
    if (_privacySummary != null) activeSensors += 2;
    if (_network != null) activeSensors += 1;
    if (activeSensors == 0) activeSensors = 8;
    return 'AURA is ready to assess this Windows PC using $activeSensors available security signal families.';
  }

  // -------------------------------------------------------------
  // Navigation & Entity Cross-Referencing
  // -------------------------------------------------------------
  void navigateTo(int index, {int? targetPid, String? targetIp, String? targetFindingId}) {
    _navigationIndex = index;
    _targetProcessPid = targetPid;
    _targetNetworkIp = targetIp;
    _targetFindingId = targetFindingId;

    if (targetPid != null) {
      inspectProcessDna(targetPid);
    }
    notifyListeners();
  }

  void _recordStoryEvent(SystemStoryEvent event) {
    _liveSystemStory.insert(0, event);
    if (_liveSystemStory.length > 50) {
      _liveSystemStory.removeLast();
    }
  }

  void _initWsListener() {
    _wsSubscription = wsService.eventStream.listen((event) {
      final type = event['type'];
      if (type == 'TELEMETRY_SNAPSHOT' && event['data'] != null) {
        final data = event['data'];
        final cpu = data['cpu_percent'] ?? 0.0;
        final procs = data['process_count'] ?? 0;
        _recordStoryEvent(
          SystemStoryEvent(
            timestamp: DateTime.now(),
            category: 'PROCESS',
            title: 'System Telemetry Pulse',
            detail: 'Active execution load: $procs processes, CPU: ${cpu.toStringAsFixed(1)}%',
          ),
        );
        notifyListeners();
      } else if (type == 'ALERT' && event['alert'] != null) {
        try {
          final alert = SecurityAlertItem.fromJson(event['alert']);
          _alerts.insert(0, alert);
          _recordStoryEvent(
            SystemStoryEvent(
              timestamp: DateTime.now(),
              category: 'SECURITY',
              title: alert.title,
              detail: alert.description,
              severity: alert.severity,
            ),
          );
          notifyListeners();
        } catch (_) {}
      }
    });
  }

  // -------------------------------------------------------------
  // 1. Establish Local Secure Session (with auto-recovery & backoff)
  // -------------------------------------------------------------
  Future<bool> authenticate([String? bootstrapCode]) async {
    _isLoading = true;
    _errorMessage = null;
    _lastTechnicalError = null;
    _sessionState = LocalSessionState.connecting;
    notifyListeners();

    int attempts = 0;
    const maxAttempts = 3;

    while (attempts < maxAttempts) {
      attempts++;
      try {
        _sessionState = LocalSessionState.authenticating;
        notifyListeners();

        _authSession = await apiService.exchangeBootstrap(bootstrapCode);
        _isAuthenticated = true;
        _sessionState = LocalSessionState.ready;
        _errorMessage = null;

        wsService.setSessionToken(_authSession!.sessionId);
        wsService.connect();

        await refreshAllData();
        _startPeriodicPolling();

        _recordStoryEvent(
          SystemStoryEvent(
            timestamp: DateTime.now(),
            category: 'SECURITY',
            title: 'Local Secure Session Established',
            detail: 'Cryptographic session handshake completed on loopback (127.0.0.1:8787).',
            severity: 'INFO',
          ),
        );

        _isLoading = false;
        notifyListeners();
        return true;
      } on AuraConnectionException catch (e) {
        _lastTechnicalError = e.technicalDetail ?? e.message;
        _errorMessage = e.message;
        if (attempts < maxAttempts) {
          await Future.delayed(Duration(milliseconds: 400 * attempts));
        }
      } on ApiException catch (e) {
        _lastTechnicalError = e.technicalDetail ?? 'API Status ${e.statusCode}: ${e.message}';
        _errorMessage = e.message;
        if (attempts < maxAttempts) {
          await Future.delayed(Duration(milliseconds: 400 * attempts));
        }
      } catch (e) {
        _lastTechnicalError = e.toString();
        _errorMessage = 'Could not establish a secure connection to the local AURA security engine.';
        if (attempts < maxAttempts) {
          await Future.delayed(Duration(milliseconds: 400 * attempts));
        }
      }
    }

    _isAuthenticated = false;
    _sessionState = LocalSessionState.failed;
    _isLoading = false;
    notifyListeners();
    return false;
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
      final prevCamActive = _privacySummary?.camera.isActive;
      final prevMicActive = _privacySummary?.microphone.isActive;

      _telemetry = await apiService.getSystemInfo();
      _privacySummary = await apiService.getPrivacySummary();

      // Detect hardware state changes for live story
      if (_privacySummary != null) {
        if (prevCamActive != null && prevCamActive != _privacySummary!.camera.isActive) {
          _recordStoryEvent(
            SystemStoryEvent(
              timestamp: DateTime.now(),
              category: 'PRIVACY',
              title: _privacySummary!.camera.isActive ? 'Camera Stream Activated' : 'Camera Stream Closed',
              detail: 'Camera sensor state changed: ${_privacySummary!.camera.summaryState}',
              severity: _privacySummary!.camera.isActive ? 'MEDIUM' : 'INFO',
            ),
          );
        }
        if (prevMicActive != null && prevMicActive != _privacySummary!.microphone.isActive) {
          _recordStoryEvent(
            SystemStoryEvent(
              timestamp: DateTime.now(),
              category: 'PRIVACY',
              title: _privacySummary!.microphone.isActive ? 'Microphone Audio Stream Active' : 'Microphone Stream Closed',
              detail: 'Audio endpoint state changed: ${_privacySummary!.microphone.summaryState}',
              severity: _privacySummary!.microphone.isActive ? 'MEDIUM' : 'INFO',
            ),
          );
        }
      }

      notifyListeners();
    } on AuraSessionExpiredException {
      _handleSessionExpired();
    } catch (_) {}
  }

  // Handle transparent background session re-authentication
  Future<void> _handleSessionExpired() async {
    if (_isAutoRecovering) return;
    _isAutoRecovering = true;
    try {
      final ok = await authenticate();
      if (!ok) {
        _isAuthenticated = false;
        _sessionState = LocalSessionState.failed;
        _errorMessage = 'Session expired. Please reconnect to local AURA engine.';
        notifyListeners();
      }
    } finally {
      _isAutoRecovering = false;
    }
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

  // -------------------------------------------------------------
  // 2. Trigger Full Security Assessment
  // -------------------------------------------------------------
  Future<FullScanReport?> runFullSecurityScan() async {
    if (_isScanning) return null;
    _isScanning = true;
    _scanProgress = 0.05;
    _scanCurrentCategory = '1. Security Foundation';
    notifyListeners();

    _recordStoryEvent(
      SystemStoryEvent(
        timestamp: DateTime.now(),
        category: 'SECURITY',
        title: 'Full Security Assessment Initiated',
        detail: 'Auditing 9 PC security dimensions across system, hardware, and network layers.',
      ),
    );

    try {
      Timer? stepTimer;
      final categories = [
        '1. Security Foundation',
        '2. Privacy Surface',
        '3. Process Activity',
        '4. Network Exposure',
        '5. Persistence Mechanisms',
        '6. Behavioural AI Analysis',
        '7. Security Event Logs',
        '8. Cross-Signal Correlation',
        '9. Evidence Synthesis',
      ];
      int step = 0;
      stepTimer = Timer.periodic(const Duration(milliseconds: 320), (_) {
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
      _scanCurrentCategory = 'Assessment Complete';
      _isScanning = false;

      _recordStoryEvent(
        SystemStoryEvent(
          timestamp: DateTime.now(),
          category: 'FINDING',
          title: 'Security Assessment Completed',
          detail: 'Score: ${report.compositeRiskScore}/100 Risk. ${report.findings.length} findings recorded.',
          severity: report.findings.any((f) => f.severity == 'CRITICAL') ? 'CRITICAL' : 'INFO',
        ),
      );

      await refreshAllData();
      notifyListeners();
      return report;
    } catch (e) {
      _isScanning = false;
      _errorMessage = 'Assessment failed to complete.';
      notifyListeners();
      return null;
    }
  }

  // -------------------------------------------------------------
  // 3. Process DNA Inspection
  // -------------------------------------------------------------
  Future<void> inspectProcessDna(int pid) async {
    _isLoadingDna = true;
    notifyListeners();
    try {
      _selectedProcessDna = await apiService.getProcessDNA(pid);
      _recordStoryEvent(
        SystemStoryEvent(
          timestamp: DateTime.now(),
          category: 'PROCESS',
          title: 'Process DNA Profile Extracted',
          detail: 'Inspected PID $pid (${_selectedProcessDna?.name ?? "Unknown"}). Risk: ${_selectedProcessDna?.riskScore ?? 0}/100',
          pid: pid,
        ),
      );
    } catch (e) {
      debugPrint('Process DNA retrieval failed for PID $pid: $e');
    } finally {
      _isLoadingDna = false;
      notifyListeners();
    }
  }

  void clearProcessDna() {
    _selectedProcessDna = null;
    _targetProcessPid = null;
    notifyListeners();
  }

  // -------------------------------------------------------------
  // 4. Safe Response Actions
  // -------------------------------------------------------------
  Future<bool> terminateProcess(int pid, [String reason = 'Operator manual termination']) async {
    try {
      final success = await apiService.terminateProcess(pid, reason);
      if (success) {
        _recordStoryEvent(
          SystemStoryEvent(
            timestamp: DateTime.now(),
            category: 'SECURITY',
            title: 'Process Safely Terminated',
            detail: 'PID $pid was terminated by operator. Reason: $reason',
            severity: 'HIGH',
            pid: pid,
          ),
        );
        await refreshAllData();
      }
      return success;
    } catch (e) {
      _errorMessage = 'Process termination failed.';
      notifyListeners();
      return false;
    }
  }

  Future<bool> openShortcut(String shortcutType) async {
    try {
      return await apiService.openWindowsShortcut(shortcutType);
    } catch (e) {
      return false;
    }
  }

  // -------------------------------------------------------------
  // 5. Incidents, Threat Hunts, Reports
  // -------------------------------------------------------------
  Future<bool> updateIncident(String incidentId, String newState) async {
    try {
      final success = await apiService.updateIncidentState(incidentId, newState);
      if (success) {
        _incidents = await apiService.getIncidents();
        _recordStoryEvent(
          SystemStoryEvent(
            timestamp: DateTime.now(),
            category: 'SECURITY',
            title: 'Incident State Updated',
            detail: 'Incident $incidentId transitioned to $newState',
          ),
        );
        notifyListeners();
      }
      return success;
    } catch (e) {
      return false;
    }
  }

  Future<bool> updateIncidentState(String incidentId, String newState) async {
    return updateIncident(incidentId, newState);
  }

  Future<void> acknowledgeAlert(String alertId) async {
    try {
      final success = await apiService.acknowledgeAlert(alertId);
      if (success) {
        _alerts = await apiService.getAlerts();
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<void> runThreatHunts() async {
    _isLoading = true;
    notifyListeners();
    try {
      _threatHunts = await apiService.runThreatHunts();
      _recordStoryEvent(
        SystemStoryEvent(
          timestamp: DateTime.now(),
          category: 'BEHAVIOUR',
          title: 'Threat Hunts Executed',
          detail: 'Evaluated 5 multi-vector threat hunting rules across memory and network.',
        ),
      );
    } catch (e) {
      _errorMessage = 'Threat hunt execution encountered an issue.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> generateReport() async {
    _isLoading = true;
    notifyListeners();
    try {
      _latestReport = await apiService.generateReport();
    } catch (e) {
      _errorMessage = 'Report compilation encountered an issue.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    _wsSubscription?.cancel();
    super.dispose();
  }
}
