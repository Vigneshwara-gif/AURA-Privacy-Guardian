import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:aura_desktop/main.dart';
import 'package:aura_desktop/services/api_service.dart';
import 'package:aura_desktop/services/websocket_service.dart';
import 'package:aura_desktop/state/aura_state_provider.dart';
import 'package:aura_desktop/widgets/severity_badge.dart';
import 'package:aura_desktop/widgets/metric_gauge.dart';

void main() {
  testWidgets('AuraDesktopApp renders authentication bootstrap gate', (WidgetTester tester) async {
    final apiService = ApiService();
    final wsService = WebSocketService();

    await tester.pumpWidget(
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

    await tester.pumpAndSettle();

    expect(find.text('AURA PRIVACY GUARDIAN'), findsOneWidget);
    expect(find.text('CONNECT LOCAL AGENT'), findsOneWidget);
  });

  testWidgets('SeverityBadge renders correct text and styling', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SeverityBadge(severity: 'CRITICAL'),
        ),
      ),
    );

    expect(find.text('CRITICAL'), findsOneWidget);
  });

  testWidgets('ScoreMetricGauge renders score and label', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ScoreMetricGauge(
            label: 'Test Defense Score',
            score: 95,
            subtitle: 'Nominal operational status',
          ),
        ),
      ),
    );

    expect(find.text('Test Defense Score'), findsOneWidget);
    expect(find.text('95/100'), findsOneWidget);
    expect(find.text('Nominal operational status'), findsOneWidget);
  });
}
