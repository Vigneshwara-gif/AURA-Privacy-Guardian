import 'package:flutter_test/flutter_test.dart';
import 'package:aura_desktop/models/auth_state.dart';
import 'package:aura_desktop/models/telemetry.dart';
import 'package:aura_desktop/models/security_posture.dart';
import 'package:aura_desktop/models/privacy.dart';
import 'package:aura_desktop/models/scan.dart';
import 'package:aura_desktop/models/process_dna.dart';
import 'package:aura_desktop/models/network_intel.dart';
import 'package:aura_desktop/models/persistence.dart';
import 'package:aura_desktop/models/threat_intel.dart';
import 'package:aura_desktop/models/incident.dart';
import 'package:aura_desktop/models/timeline.dart';
import 'package:aura_desktop/models/alert.dart';
import 'package:aura_desktop/models/report.dart';
import 'package:aura_desktop/models/analytics.dart';

void main() {
  test('AuthSession fromJson', () {
    final s = AuthSession.fromJson({
      'session_id': 'SES-12345',
      'issued_to': 'TestOperator',
      'scope': 'OPERATOR',
      'expires_at': '2026-08-27T18:00:00Z',
    });
    expect(s.sessionId, 'SES-12345');
    expect(s.scope, 'OPERATOR');
  });

  test('SystemTelemetry fromJson', () {
    final t = SystemTelemetry.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'os_name': 'Windows',
      'os_version': '10.0.26200',
      'os_build': '26200.9168',
      'os_display_version': 'Windows 11 Pro 25H2',
      'architecture': 'AMD64',
      'hostname': 'AURA-HOST',
      'physical_cores': 8,
      'logical_cores': 16,
      'cpu_percent': 12.5,
      'per_core_cpu_percent': [10.0, 15.0],
      'memory_percent': 48.0,
      'memory_used_bytes': 8000000000,
      'memory_total_bytes': 16000000000,
      'disk_used_bytes': 100000000000,
      'disk_total_bytes': 500000000000,
      'disk_percent': 20.0,
      'uptime_seconds': 3600.0,
    });
    expect(t.hostname, 'AURA-HOST');
    expect(t.cpuPercent, 12.5);
    expect(t.logicalCores, 16);
  });

  test('SecurityPosture fromJson', () {
    final p = SecurityPosture.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'defender': {
        'realtime_protection_enabled': true,
        'antivirus_enabled': true,
        'behavior_monitor_enabled': true,
        'ioav_protection_enabled': true,
        'nis_enabled': true,
      },
      'firewall': {
        'domain_profile_enabled': true,
        'private_profile_enabled': true,
        'public_profile_enabled': true,
        'all_profiles_secure': true,
      },
      'secure_boot_enabled': true,
      'tpm_present': true,
      'uac_enabled': true,
      'pending_reboot': false,
      'overall_posture_score': 100,
      'posture_level': 'OPTIMAL',
    });
    expect(p.defender.realtimeProtectionEnabled, isTrue);
    expect(p.firewall.allProfilesSecure, isTrue);
    expect(p.overallPostureScore, 100);
  });

  test('PrivacySummary fromJson', () {
    final priv = PrivacySummary.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'camera': {
        'timestamp': '2026-08-27T16:00:00Z',
        'status': 'AVAILABLE',
        'device_count': 1,
        'devices': [],
        'system_permission': 'ALLOWED',
        'is_active': false,
        'active_pids': [],
        'recent_usage': [],
        'detail': '1 camera device(s) enumerated.',
      },
      'microphone': {
        'timestamp': '2026-08-27T16:00:00Z',
        'status': 'AVAILABLE',
        'device_count': 19,
        'devices': [],
        'system_permission': 'ALLOWED',
        'is_active': false,
        'active_pids': [],
        'recent_usage': [],
        'detail': '19 audio input endpoint(s) enumerated.',
      },
      'overall_privacy_score': 100,
    });
    expect(priv.camera.deviceCount, 1);
    expect(priv.microphone.deviceCount, 19);
    expect(priv.overallPrivacyScore, 100);
  });

  test('FullScanReport and SecurityFinding fromJson', () {
    final report = FullScanReport.fromJson({
      'scan_id': 'SCN-12345',
      'initiated_at': '2026-08-27T16:00:00Z',
      'completed_at': '2026-08-27T16:00:02Z',
      'duration_seconds': 2.1,
      'checks_count': 16,
      'categories_scanned': ['ANTIVIRUS', 'FIREWALL'],
      'overall_security_score': 95,
      'privacy_health_score': 100,
      'composite_risk_score': 5,
      'risk_level': 'NORMAL',
      'findings': [
        {
          'finding_id': 'FND-001',
          'title': 'Test Finding',
          'category': 'NETWORK',
          'severity': 'LOW',
          'confidence': 0.9,
          'timestamp': '2026-08-27T16:00:00Z',
          'affected_entity': 'Port 443',
          'explanation': 'Test explanation',
          'recommendation': 'Test recommendation',
          'remediation_status': 'OPEN',
        }
      ],
      'narrative_summary': 'System is secure.',
    });
    expect(report.scanId, 'SCN-12345');
    expect(report.findings.length, 1);
    expect(report.findings[0].findingId, 'FND-001');
  });

  test('ProcessDNAProfile fromJson', () {
    final dna = ProcessDNAProfile.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'pid': 1234,
      'identity': {
        'pid': 1234,
        'name': 'python.exe',
        'exe_exists': true,
        'child_pids': [],
        'created_time': '2026-08-27T16:00:00Z',
        'lifetime_seconds': 120.0,
        'is_elevated': false,
      },
      'execution': {
        'cpu_percent': 1.5,
        'memory_rss_bytes': 50000000,
        'memory_mb': 50.0,
        'num_threads': 4,
        'num_handles': 100,
        'status': 'running',
      },
      'security': {
        'rules_triggered': [],
        'ml_anomaly_score': 0.05,
        'baseline_deviation': 0.0,
        'risk_score': 0,
        'risk_level': 'NORMAL',
        'evidences': [],
      },
    });
    expect(dna.pid, 1234);
    expect(dna.identity.name, 'python.exe');
    expect(dna.execution.cpuPercent, 1.5);
  });

  test('NetworkInvestigation fromJson', () {
    final net = NetworkInvestigation.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'total_connections': 10,
      'established_count': 5,
      'listening_count': 5,
      'remote_public_count': 2,
      'active_endpoints': [],
      'exposure_findings': [],
      'summary': 'Network analyzed',
    });
    expect(net.totalConnections, 10);
    expect(net.establishedCount, 5);
  });

  test('PersistenceAnalysis fromJson', () {
    final pers = PersistenceAnalysis.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'total_startup_apps': 5,
      'total_services': 100,
      'total_scheduled_tasks': 50,
      'analyzed_items': [],
      'suspicious_count': 0,
      'summary': 'Clean auto-starts',
    });
    expect(pers.totalStartupApps, 5);
    expect(pers.suspiciousCount, 0);
  });

  test('AnomalyExplanation and ThreatHuntResult fromJson', () {
    final exp = AnomalyExplanation.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'is_anomaly': false,
      'combined_score': 0.1,
      'isolation_forest_score': 0.1,
      'lof_score': 0.1,
      'confidence': 0.95,
      'feature_explanations': [],
      'narrative': 'Nominal',
    });
    expect(exp.isAnomaly, isFalse);

    final hunts = ThreatHuntResult.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'hunts_executed': 5,
      'matches_found': 0,
      'matches': [],
      'summary': 'Zero threat matches',
    });
    expect(hunts.huntsExecuted, 5);
  });

  test('IncidentItem, TimelineEvent, SecurityAlertItem, Report, Analytics fromJson', () {
    final inc = IncidentItem.fromJson({
      'incident_id': 'INC-001',
      'title': 'Test Incident',
      'severity': 'LOW',
      'state': 'NEW',
      'created_at': '2026-08-27T16:00:00Z',
      'updated_at': '2026-08-27T16:00:00Z',
      'summary': 'Test',
      'affected_entities': ['Host'],
      'findings_count': 1,
      'recommended_actions': [],
    });
    expect(inc.incidentId, 'INC-001');

    final tlm = TimelineEvent.fromJson({
      'item_id': 'TLM-001',
      'timestamp': '2026-08-27T16:00:00Z',
      'event_type': 'PROCESS_START',
      'severity': 'INFO',
      'title': 'Process started',
      'entity_name': 'python.exe',
      'entity_id': '1234',
    });
    expect(tlm.itemId, 'TLM-001');

    final alt = SecurityAlertItem.fromJson({
      'alert_id': 'ALT-001',
      'title': 'Alert',
      'severity': 'INFO',
      'timestamp': '2026-08-27T16:00:00Z',
      'source': 'POSTURE',
      'summary': 'Alert summary',
      'entity_id': 'HOST',
      'is_acknowledged': false,
    });
    expect(alt.alertId, 'ALT-001');

    final rep = SecurityAuditReport.fromJson({
      'report_id': 'REP-001',
      'generated_at': '2026-08-27T16:00:00Z',
      'hostname': 'AURA-HOST',
      'os_name': 'Windows',
      'os_build': '26200',
      'executive_summary': 'Healthy',
      'overall_security_score': 100,
      'privacy_health_score': 100,
      'composite_risk_score': 0,
      'risk_level': 'NORMAL',
      'sections': {},
    });
    expect(rep.reportId, 'REP-001');

    final an = AnalyticsOverview.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'time_window': '24h',
      'current_security_score': 100,
      'current_privacy_score': 100,
      'current_composite_risk': 0,
      'total_findings_count': 0,
      'open_findings_count': 0,
      'resolved_findings_count': 0,
      'critical_findings_count': 0,
      'high_findings_count': 0,
      'medium_findings_count': 0,
      'low_findings_count': 0,
      'findings_by_category': {},
    });
    expect(an.currentSecurityScore, 100);
  });

  test('SystemTelemetry process count resolution and fallback', () {
    final t1 = SystemTelemetry.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'total_processes': 378,
      'cpu_overall_percent': 15.2,
      'memory_used_gb': 12.5,
      'memory_total_gb': 16.0,
    });
    expect(t1.processCount, 378);
    expect(t1.totalProcesses, 378);

    final t2 = SystemTelemetry.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'active_processes': 142,
    });
    expect(t2.processCount, 142);
  });

  test('Camera and Microphone device list and summary state consistency', () {
    final cam = CameraIntelligence.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'status': 'AVAILABLE',
      'devices': [
        {'index': '0', 'name': 'HP HD Camera', 'provider': 'Microsoft', 'driver_version': '10.0', 'matching_id': 'USB\\VID_04F2'}
      ],
      'system_permission': 'ALLOWED',
      'is_active': false,
    });
    expect(cam.deviceCount, 1);
    expect(cam.summaryState, 'Ready & Idle');

    final mic = MicrophoneIntelligence.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'status': 'AVAILABLE',
      'endpoints': [
        {'index': '001', 'name': 'Realtek Audio', 'provider': 'Realtek', 'driver_version': '6.0', 'matching_id': 'HDAUDIO\\FUNC_01'}
      ],
      'system_permission': 'ALLOWED',
      'is_active': false,
    });
    expect(mic.deviceCount, 1);
    expect(mic.summaryState, 'Ready & Idle');
  });

  test('NetworkInvestigation count getters', () {
    final net = NetworkInvestigation.fromJson({
      'timestamp': '2026-08-27T16:00:00Z',
      'total_connections': 175,
      'established_count': 43,
      'listening_count': 38,
      'remote_public_count': 15,
      'active_endpoints': [],
      'exposure_findings': [],
      'summary': '175 sockets evaluated',
    });
    expect(net.activeConnectionsCount, 175);
    expect(net.listeningPortsCount, 38);
    expect(net.publicIpCount, 15);
  });
}
