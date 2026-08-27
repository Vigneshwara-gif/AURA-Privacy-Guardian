import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../core/utils/formatters.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';

class AlertsView extends StatelessWidget {
  const AlertsView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final alerts = state.alerts;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AuraCard(
            title: 'Real-Time Alert Center & Notification Ledger',
            icon: Icons.notifications_active_rounded,
            child: Text(
              'Real-time alerts with deduplication, cooldown windows, and operator acknowledgement actions.',
              style: const TextStyle(fontSize: 13, color: AuraTheme.textSecondary),
            ),
          ),
          const SizedBox(height: 24),

          if (alerts.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(
                child: Text('Zero active alerts. System is operating peacefully.', style: TextStyle(color: AuraTheme.healthy)),
              ),
            )
          else
            Column(
              children: alerts.map((a) {
                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AuraTheme.surface,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AuraTheme.borderSubtle),
                  ),
                  child: Row(
                    children: [
                      SeverityBadge(severity: a.severity),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(a.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
                            Text('${a.summary} (Entity: ${a.entityId})', style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
                          ],
                        ),
                      ),
                      Text(Formatters.formatTimeOnly(a.timestamp), style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
                      const SizedBox(width: 16),
                      if (!a.isAcknowledged)
                        OutlinedButton(
                          onPressed: () => state.acknowledgeAlert(a.alertId),
                          child: const Text('ACKNOWLEDGE', style: TextStyle(fontSize: 10)),
                        )
                      else
                        const Text('ACKNOWLEDGED', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AuraTheme.healthy)),
                    ],
                  ),
                );
              }).toList(),
            ),
        ],
      ),
    );
  }
}
