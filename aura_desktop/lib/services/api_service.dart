import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../core/constants/api_constants.dart';
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

class ApiException implements Exception {
  final int statusCode;
  final String message;
  final String? technicalDetail;

  ApiException(this.statusCode, this.message, {this.technicalDetail});

  @override
  String toString() => message;
}

class AuraConnectionException implements Exception {
  final String message;
  final String? technicalDetail;

  AuraConnectionException(this.message, {this.technicalDetail});

  @override
  String toString() => message;
}

class AuraSessionExpiredException implements Exception {
  final String message;
  AuraSessionExpiredException([this.message = 'Local secure session has expired.']);

  @override
  String toString() => message;
}

class ApiService {
  final String baseUrl;
  String? _sessionToken;

  static const List<String> _localBootstrapCandidates = [
    'local-dev',
    'LOCAL_OPERATOR_DEV_SESSION',
    'local-desktop',
    'aura-local-session',
  ];

  ApiService({this.baseUrl = ApiConstants.defaultBaseUrl});

  void setSessionToken(String? token) {
    _sessionToken = token;
  }

  String? get sessionToken => _sessionToken;

  Map<String, String> get _headers {
    final h = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (_sessionToken != null && _sessionToken!.isNotEmpty) {
      h['Authorization'] = 'Bearer $_sessionToken';
    }
    return h;
  }

  // -------------------------------------------------------------
  // 0. Probe API Connectivity
  // -------------------------------------------------------------
  Future<bool> probeHealth() async {
    try {
      final res = await http.get(
        Uri.parse('$baseUrl/api/v1/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 3));

      return res.statusCode == 200 || res.statusCode == 401;
    } catch (_) {
      return false;
    }
  }

  // -------------------------------------------------------------
  // 1. Auth: Exchange Bootstrap Code for Session Token
  // -------------------------------------------------------------
  Future<AuthSession> exchangeBootstrap(String? bootstrapCode, {String clientName = 'AuraDesktopApp'}) async {
    final candidates = <String>[];
    if (bootstrapCode != null && bootstrapCode.trim().isNotEmpty) {
      candidates.add(bootstrapCode.trim());
    }
    for (final code in _localBootstrapCandidates) {
      if (!candidates.contains(code)) {
        candidates.add(code);
      }
    }

    String? lastError;

    for (final code in candidates) {
      try {
        final res = await http.post(
          Uri.parse('$baseUrl${ApiConstants.authSession}'),
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-AURA-BOOTSTRAP': code,
          },
          body: jsonEncode({'client_name': clientName}),
        ).timeout(const Duration(seconds: 4));

        if (res.statusCode == 200) {
          final session = AuthSession.fromJson(jsonDecode(res.body));
          _sessionToken = session.sessionId;
          return session;
        } else {
          lastError = 'HTTP ${res.statusCode}';
        }
      } on SocketException catch (e) {
        throw AuraConnectionException(
          'AURA Security Engine is not reachable on this PC (127.0.0.1:8787). Please ensure the background service is running.',
          technicalDetail: 'SocketException: ${e.message}',
        );
      } on TimeoutException {
        throw AuraConnectionException(
          'Connection to local AURA engine timed out. The service may be starting up.',
          technicalDetail: 'TimeoutException: Request exceeded 4s threshold',
        );
      } catch (e) {
        lastError = e.toString();
      }
    }

    throw ApiException(
      401,
      'Could not establish a secure session with the local AURA engine. Please ensure the agent is running.',
      technicalDetail: lastError,
    );
  }

  // -------------------------------------------------------------
  // Internal Request Helpers with Automatic 401 Detection
  // -------------------------------------------------------------
  Future<http.Response> _get(String path) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl$path'), headers: _headers).timeout(const Duration(seconds: 6));
      if (res.statusCode == 401) {
        _sessionToken = null;
        throw AuraSessionExpiredException();
      }
      return res;
    } on SocketException catch (e) {
      throw AuraConnectionException('Local AURA service disconnected.', technicalDetail: e.message);
    } on TimeoutException {
      throw AuraConnectionException('Request to local AURA service timed out.');
    }
  }

  Future<http.Response> _post(String path, [Map<String, dynamic>? body]) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl$path'),
        headers: _headers,
        body: body != null ? jsonEncode(body) : null,
      ).timeout(const Duration(seconds: 15));
      if (res.statusCode == 401) {
        _sessionToken = null;
        throw AuraSessionExpiredException();
      }
      return res;
    } on SocketException catch (e) {
      throw AuraConnectionException('Local AURA service disconnected.', technicalDetail: e.message);
    } on TimeoutException {
      throw AuraConnectionException('Request to local AURA service timed out.');
    }
  }

  // -------------------------------------------------------------
  // 2. System Telemetry
  // -------------------------------------------------------------
  Future<SystemTelemetry> getSystemInfo() async {
    final res = await _get(ApiConstants.systemInfo);
    if (res.statusCode == 200) {
      return SystemTelemetry.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to fetch system telemetry.');
  }

  // -------------------------------------------------------------
  // 3. Security Posture
  // -------------------------------------------------------------
  Future<SecurityPosture> getSecurityPosture() async {
    final res = await _get(ApiConstants.securityPosture);
    if (res.statusCode == 200) {
      return SecurityPosture.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to fetch security posture.');
  }

  // -------------------------------------------------------------
  // 4. Privacy Intelligence
  // -------------------------------------------------------------
  Future<CameraIntelligence> getCameraIntelligence() async {
    final res = await _get(ApiConstants.privacyCamera);
    if (res.statusCode == 200) {
      return CameraIntelligence.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to query camera sentinel.');
  }

  Future<MicrophoneIntelligence> getMicrophoneIntelligence() async {
    final res = await _get(ApiConstants.privacyMicrophone);
    if (res.statusCode == 200) {
      return MicrophoneIntelligence.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to query microphone sentinel.');
  }

  Future<PrivacySummary> getPrivacySummary() async {
    final res = await _get(ApiConstants.privacySummary);
    if (res.statusCode == 200) {
      return PrivacySummary.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to fetch privacy summary.');
  }

  // -------------------------------------------------------------
  // 5. Scans & Findings
  // -------------------------------------------------------------
  Future<FullScanReport> triggerFullScan() async {
    final res = await _post(ApiConstants.scanFull);
    if (res.statusCode == 200) {
      return FullScanReport.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Security audit failed to execute.');
  }

  Future<FullScanReport> getLatestScan() async {
    final res = await _get(ApiConstants.scanLatest);
    if (res.statusCode == 200) {
      return FullScanReport.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to load latest scan report.');
  }

  Future<List<SecurityFinding>> getFindings() async {
    final res = await _get(ApiConstants.securityFindings);
    if (res.statusCode == 200) {
      final List<dynamic> list = jsonDecode(res.body);
      return list.map((e) => SecurityFinding.fromJson(e)).toList();
    }
    throw ApiException(res.statusCode, 'Failed to load security findings.');
  }

  // -------------------------------------------------------------
  // 6. Process Intelligence & DNA
  // -------------------------------------------------------------
  Future<List<dynamic>> getProcessTree() async {
    final res = await _get(ApiConstants.processTree);
    if (res.statusCode == 200) {
      return jsonDecode(res.body) as List<dynamic>;
    }
    throw ApiException(res.statusCode, 'Failed to load process tree.');
  }

  Future<ProcessDNAProfile> getProcessDNA(int pid) async {
    final res = await _get(ApiConstants.processDna(pid));
    if (res.statusCode == 200) {
      return ProcessDNAProfile.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to extract Process DNA for PID $pid.');
  }

  // -------------------------------------------------------------
  // 7. Network Investigation
  // -------------------------------------------------------------
  Future<NetworkInvestigation> investigateNetwork() async {
    final res = await _get(ApiConstants.networkInvestigate);
    if (res.statusCode == 200) {
      return NetworkInvestigation.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to analyze network topology.');
  }

  // -------------------------------------------------------------
  // 8. Persistence Analysis
  // -------------------------------------------------------------
  Future<PersistenceAnalysis> analyzePersistence() async {
    final res = await _get(ApiConstants.persistenceAnalysis);
    if (res.statusCode == 200) {
      return PersistenceAnalysis.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to inspect persistence inventory.');
  }

  // -------------------------------------------------------------
  // 9. AI Explainability & Threat Hunting
  // -------------------------------------------------------------
  Future<AnomalyExplanation> getAiExplanation() async {
    final res = await _get(ApiConstants.aiExplain);
    if (res.statusCode == 200) {
      return AnomalyExplanation.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to query AI anomaly explanation.');
  }

  Future<ThreatHuntResult> runThreatHunts() async {
    final res = await _post(ApiConstants.threatHuntsRun);
    if (res.statusCode == 200) {
      return ThreatHuntResult.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to execute threat hunting queries.');
  }

  // -------------------------------------------------------------
  // 10. Incidents & Response Actions
  // -------------------------------------------------------------
  Future<List<IncidentItem>> getIncidents() async {
    final res = await _get(ApiConstants.incidents);
    if (res.statusCode == 200) {
      final List<dynamic> list = jsonDecode(res.body);
      return list.map((e) => IncidentItem.fromJson(e)).toList();
    }
    throw ApiException(res.statusCode, 'Failed to load incident cases.');
  }

  Future<bool> updateIncidentState(String incidentId, String newState) async {
    final res = await _post(ApiConstants.incidentState(incidentId), {'state': newState});
    return res.statusCode == 200;
  }

  Future<bool> terminateProcess(int pid, [String reason = 'Operator action']) async {
    final res = await _post(ApiConstants.terminateProcess, {'pid': pid, 'reason': reason});
    return res.statusCode == 200;
  }

  Future<bool> openWindowsShortcut(String shortcutType) async {
    final res = await _post(ApiConstants.openShortcut, {'shortcut_type': shortcutType});
    return res.statusCode == 200;
  }

  // -------------------------------------------------------------
  // 11. Timeline & Alerts
  // -------------------------------------------------------------
  Future<List<TimelineEvent>> getTimeline() async {
    final res = await _get(ApiConstants.timeline);
    if (res.statusCode == 200) {
      final List<dynamic> list = jsonDecode(res.body);
      return list.map((e) => TimelineEvent.fromJson(e)).toList();
    }
    throw ApiException(res.statusCode, 'Failed to fetch forensic timeline.');
  }

  Future<List<SecurityAlertItem>> getAlerts() async {
    final res = await _get(ApiConstants.alerts);
    if (res.statusCode == 200) {
      final List<dynamic> list = jsonDecode(res.body);
      return list.map((e) => SecurityAlertItem.fromJson(e)).toList();
    }
    throw ApiException(res.statusCode, 'Failed to load alert feed.');
  }

  Future<bool> acknowledgeAlert(String alertId) async {
    final res = await _post(ApiConstants.alertAck(alertId));
    return res.statusCode == 200;
  }

  // -------------------------------------------------------------
  // 12. Analytics & Reports
  // -------------------------------------------------------------
  Future<AnalyticsOverview> getAnalyticsOverview() async {
    final res = await _get(ApiConstants.analyticsOverview);
    if (res.statusCode == 200) {
      return AnalyticsOverview.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to load security analytics.');
  }

  Future<SecurityAuditReport> generateReport() async {
    final res = await _post(ApiConstants.reportGenerate);
    if (res.statusCode == 200) {
      return SecurityAuditReport.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, 'Failed to compile audit report.');
  }
}
