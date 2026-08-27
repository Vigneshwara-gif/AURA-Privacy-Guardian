import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:aura_desktop/core/theme/aura_theme.dart';
import 'package:aura_desktop/services/api_service.dart';
import 'package:aura_desktop/services/websocket_service.dart';
import 'package:aura_desktop/state/aura_state_provider.dart';
import 'package:aura_desktop/views/overview_view.dart';
import 'package:aura_desktop/views/scan_view.dart';
import 'package:aura_desktop/views/threat_intel_view.dart';
import 'package:aura_desktop/views/privacy_sentinel_view.dart';
import 'package:aura_desktop/views/process_intel_view.dart';
import 'package:aura_desktop/views/network_intel_view.dart';
import 'package:aura_desktop/views/persistence_view.dart';
import 'package:aura_desktop/views/incidents_view.dart';
import 'package:aura_desktop/views/timeline_view.dart';
import 'package:aura_desktop/views/reports_view.dart';
import 'package:aura_desktop/views/alerts_view.dart';
import 'package:aura_desktop/views/security_events_view.dart';
import 'package:aura_desktop/views/onboarding_view.dart';
import 'package:aura_desktop/views/settings_view.dart';

Widget createTestApp(Widget child) {
  final api = ApiService();
  final ws = WebSocketService();
  final state = AuraStateProvider(apiService: api, wsService: ws);

  return MultiProvider(
    providers: [
      ChangeNotifierProvider.value(value: state),
    ],
    child: MaterialApp(
      theme: AuraTheme.darkTheme,
      home: Scaffold(body: child),
    ),
  );
}

void setDesktopViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1920, 1080);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

void main() {
  testWidgets('OverviewView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const OverviewView()));
    expect(find.textContaining('AURA SECURITY STATUS'), findsOneWidget);
    expect(find.text('Security Health'), findsOneWidget);
  });

  testWidgets('ScanView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const ScanView()));
    expect(find.textContaining('Full PC Security'), findsOneWidget);
  });

  testWidgets('ThreatIntelView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const ThreatIntelView()));
    expect(find.textContaining('Dual-Model Ensemble'), findsOneWidget);
  });

  testWidgets('PrivacySentinelView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const PrivacySentinelView()));
    expect(find.textContaining('ZERO-MEDIA CAPTURE'), findsOneWidget);
  });

  testWidgets('ProcessIntelView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const ProcessIntelView()));
    expect(find.textContaining('Process DNA'), findsOneWidget);
  });

  testWidgets('NetworkIntelView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const NetworkIntelView()));
    expect(find.textContaining('Socket Flow Investigation'), findsOneWidget);
  });

  testWidgets('PersistenceView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const PersistenceView()));
    expect(find.textContaining('Auto-Start & Persistence'), findsOneWidget);
  });

  testWidgets('IncidentsView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const IncidentsView()));
    expect(find.textContaining('Security Incident Studio'), findsOneWidget);
  });

  testWidgets('TimelineView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const TimelineView()));
    expect(find.textContaining('Forensic Chronological'), findsOneWidget);
  });

  testWidgets('ReportsView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const ReportsView()));
    expect(find.textContaining('Security Audit & Technical Report'), findsOneWidget);
  });

  testWidgets('AlertsView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const AlertsView()));
    expect(find.textContaining('Real-Time Alert Center'), findsOneWidget);
  });

  testWidgets('SecurityEventsView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const SecurityEventsView()));
    expect(find.textContaining('Real-Time Security Event Center'), findsOneWidget);
  });

  testWidgets('OnboardingView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(OnboardingView(onFinish: () {})));
    expect(find.textContaining('AURA PRIVACY GUARDIAN'), findsOneWidget);
    expect(find.text('GET STARTED'), findsOneWidget);
  });

  testWidgets('SettingsView renders without throwing exceptions', (tester) async {
    setDesktopViewport(tester);
    await tester.pumpWidget(createTestApp(const SettingsView()));
    expect(find.textContaining('Agent Preferences'), findsOneWidget);
  });
}
