import 'dart:convert';
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
  ApiException(this.statusCode, this.message);
  @override
  String toString() => 'ApiException ($statusCode): $message';
}

class ApiService {
  final String baseUrl;
  String? _sessionToken;

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
    if (_sessionToken != null) {
      h['Authorization'] = 'Bearer $_sessionToken';
    }
    return h;
  }

  // 1. Auth: Exchange Bootstrap Code for Session
  Future<AuthSession> exchangeBootstrap(String bootstrapCode, {String clientName = 'AuraDesktopApp'}) async {
    final res = await http.post(
      Uri.parse('$baseUrl${ApiConstants.authSession}'),
      headers: {
        'Content-Type': 'application/json',
        'X-AURA-BOOTSTRAP': bootstrapCode,
      },
      body: jsonEncode({'client_name': clientName}),
    );
    if (res.statusCode == 200) {
      final session = AuthSession.fromJson(jsonDecode(res.body));
      _sessionToken = session.sessionId;
      return session;
    } else {
      throw ApiException(res.statusCode, 'Failed to authenticate bootstrap token: ${res.body}');
    }
  }

  // 2. System Telemetry
  Future<SystemTelemetry> getSystemInfo() async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.systemInfo}'), headers: _headers);
    if (res.statusCode == 200) {
      return SystemTelemetry.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }

  // 3. Security Posture
  Future<SecurityPosture> getSecurityPosture() async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.securityPosture}'), headers: _headers);
    if (res.statusCode == 200) {
      return SecurityPosture.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }

  // 4. Privacy Intelligence
  Future<CameraIntelligence> getCameraIntelligence() async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.privacyCamera}'), headers: _headers);
    if (res.statusCode == 200) {
      return CameraIntelligence.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }

  Future<MicrophoneIntelligence> getMicrophoneIntelligence() async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.privacyMicrophone}'), headers: _headers);
    if (res.statusCode == 200) {
      return MicrophoneIntelligence.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }

  Future<PrivacySummary> getPrivacySummary() async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.privacySummary}'), headers: _headers);
    if (res.statusCode == 200) {
      return PrivacySummary.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }

  // 5. Full Security Scan
  Future<FullScanReport> triggerFullScan() async {
    final res = await http.post(Uri.parse('$baseUrl${ApiConstants.scanFull}'), headers: _headers);
    if (res.statusCode == 200) {
      return FullScanReport.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }

  Future<FullScanReport?> getLatestScan() async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.scanLatest}'), headers: _headers);
    if (res.statusCode == 200) {
      return FullScanReport.fromJson(jsonDecode(res.body));
    }
    return null;
  }

  Future<List<SecurityFinding>> getFindings({int limit = 50}) async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.securityFindings}?limit=$limit'), headers: _headers);
    if (res.statusCode == 200) {
      final List list = jsonDecode(res.body);
      return list.map((e) => SecurityFinding.fromJson(e)).toList();
    }
    throw ApiException(res.statusCode, res.body);
  }

  // 6. Process Intelligence
  Future<List<dynamic>> getProcessTree() async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.processTree}'), headers: _headers);
    if (res.statusCode == 200) {
      return jsonDecode(res.body);
    }
    throw ApiException(res.statusCode, res.body);
  }

  Future<ProcessDNAProfile> getProcessDna(int pid) async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.processDna(pid)}'), headers: _headers);
    if (res.statusCode == 200) {
      return ProcessDNAProfile.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }

  // 7. Network Investigation
  Future<NetworkInvestigation> investigateNetwork({int limit = 100}) async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.networkInvestigate}?limit=$limit'), headers: _headers);
    if (res.statusCode == 200) {
      return NetworkInvestigation.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }

  // 8. Persistence Intelligence
  Future<PersistenceAnalysis> analyzePersistence() async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.persistenceAnalysis}'), headers: _headers);
    if (res.statusCode == 200) {
      return PersistenceAnalysis.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }

  // 9. Threat Hunting & Explainability
  Future<ThreatHuntResult> runThreatHunts() async {
    final res = await http.post(Uri.parse('$baseUrl${ApiConstants.threatHuntsRun}'), headers: _headers);
    if (res.statusCode == 200) {
      return ThreatHuntResult.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }

  Future<AnomalyExplanation> getAiExplanation() async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.aiExplain}'), headers: _headers);
    if (res.statusCode == 200) {
      return AnomalyExplanation.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }

  // 10. Incidents
  Future<List<IncidentItem>> getIncidents({int limit = 50}) async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.incidents}?limit=$limit'), headers: _headers);
    if (res.statusCode == 200) {
      final List list = jsonDecode(res.body);
      return list.map((e) => IncidentItem.fromJson(e)).toList();
    }
    throw ApiException(res.statusCode, res.body);
  }

  Future<bool> updateIncidentState(String incidentId, String newState, {String note = ''}) async {
    final res = await http.post(
      Uri.parse('$baseUrl${ApiConstants.incidentState(incidentId)}'),
      headers: _headers,
      body: jsonEncode({'state': newState, 'note': note}),
    );
    return res.statusCode == 200;
  }

  // 11. Timeline
  Future<List<TimelineEvent>> getTimeline({int limit = 50, String? severity}) async {
    var url = '$baseUrl${ApiConstants.timeline}?limit=$limit';
    if (severity != null) url += '&severity=$severity';
    final res = await http.get(Uri.parse(url), headers: _headers);
    if (res.statusCode == 200) {
      final List list = jsonDecode(res.body);
      return list.map((e) => TimelineEvent.fromJson(e)).toList();
    }
    throw ApiException(res.statusCode, res.body);
  }

  // 12. Alerts
  Future<List<SecurityAlertItem>> getAlerts({int limit = 50}) async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.alerts}?limit=$limit'), headers: _headers);
    if (res.statusCode == 200) {
      final List list = jsonDecode(res.body);
      return list.map((e) => SecurityAlertItem.fromJson(e)).toList();
    }
    throw ApiException(res.statusCode, res.body);
  }

  Future<bool> acknowledgeAlert(String alertId) async {
    final res = await http.post(Uri.parse('$baseUrl${ApiConstants.alertAck(alertId)}'), headers: _headers);
    return res.statusCode == 200;
  }

  // 13. Safe Response Actions
  Future<Map<String, dynamic>> terminateProcess(int pid) async {
    final res = await http.post(
      Uri.parse('$baseUrl${ApiConstants.terminateProcess}'),
      headers: _headers,
      body: jsonEncode({'pid': pid}),
    );
    if (res.statusCode == 200) {
      return jsonDecode(res.body);
    }
    throw ApiException(res.statusCode, res.body);
  }

  Future<Map<String, dynamic>> openShortcut(String shortcutType) async {
    final res = await http.post(
      Uri.parse('$baseUrl${ApiConstants.openShortcut}'),
      headers: _headers,
      body: jsonEncode({'shortcut_type': shortcutType}),
    );
    if (res.statusCode == 200) {
      return jsonDecode(res.body);
    }
    throw ApiException(res.statusCode, res.body);
  }

  // 14. Analytics & Reports
  Future<AnalyticsOverview> getAnalyticsOverview({String timeWindow = '24h'}) async {
    final res = await http.get(Uri.parse('$baseUrl${ApiConstants.analyticsOverview}?time_window=$timeWindow'), headers: _headers);
    if (res.statusCode == 200) {
      return AnalyticsOverview.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }

  Future<SecurityAuditReport> generateReport() async {
    final res = await http.post(Uri.parse('$baseUrl${ApiConstants.reportGenerate}'), headers: _headers);
    if (res.statusCode == 200) {
      return SecurityAuditReport.fromJson(jsonDecode(res.body));
    }
    throw ApiException(res.statusCode, res.body);
  }
}
