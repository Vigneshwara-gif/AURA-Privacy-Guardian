class ApiConstants {
  static const String defaultBaseUrl = 'http://127.0.0.1:8787';
  static const String defaultWsUrl = 'ws://127.0.0.1:8787/api/v1/stream/ws';

  // Auth
  static const String authSession = '/api/v1/auth/session';

  // Master 1 System & Scanners
  static const String systemInfo = '/api/v1/system/info';
  static const String processTree = '/api/v1/processes/tree';
  static const String persistenceInventory = '/api/v1/persistence/inventory';
  static const String securityPosture = '/api/v1/security/posture';
  static const String eventLogs = '/api/v1/logs/windows/recent';
  static const String scanFull = '/api/v1/scan/full';
  static const String scanLatest = '/api/v1/scan/full/latest';
  static const String securityFindings = '/api/v1/security/findings';

  // Privacy Sentinels
  static const String privacyCamera = '/api/v1/privacy/camera';
  static const String privacyMicrophone = '/api/v1/privacy/microphone';
  static const String privacySummary = '/api/v1/privacy/summary';

  // Master 2 Intelligence
  static String processDna(int pid) => '/api/v1/processes/$pid/dna';
  static const String networkInvestigate = '/api/v1/network/investigate';
  static const String persistenceAnalysis = '/api/v1/persistence/analysis';
  static const String threatHuntsRun = '/api/v1/threats/hunts/run';
  static const String aiExplain = '/api/v1/ai/explain';
  static const String timeline = '/api/v1/timeline';
  static const String incidents = '/api/v1/incidents';
  static String incidentState(String id) => '/api/v1/incidents/$id/state';
  static const String terminateProcess = '/api/v1/response/terminate-process';
  static const String openShortcut = '/api/v1/response/open-shortcut';
  static const String alerts = '/api/v1/alerts';
  static String alertAck(String id) => '/api/v1/alerts/$id/acknowledge';
  static const String analyticsOverview = '/api/v1/analytics/overview';
  static const String reportGenerate = '/api/v1/reports/generate';
}
