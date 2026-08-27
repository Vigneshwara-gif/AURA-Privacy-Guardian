import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../core/utils/formatters.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';

class TimelineView extends StatelessWidget {
  const TimelineView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final events = state.timelineEvents;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AuraCard(
            title: 'Forensic Chronological Security Timeline',
            icon: Icons.timeline_rounded,
            child: Text(
              'Unified chronological ledger of process starts, network connections, hardware privacy sessions, and posture modifications.',
              style: const TextStyle(fontSize: 13, color: AuraTheme.textSecondary),
            ),
          ),
          const SizedBox(height: 24),

          if (events.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(
                child: Text('No timeline events recorded.', style: TextStyle(color: AuraTheme.textSecondary)),
              ),
            )
          else
            Column(
              children: events.map((e) {
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
                      SeverityBadge(severity: e.severity, compact: true),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(e.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
                            Text('Entity: ${e.entityName} (${e.entityId}) | Type: ${e.eventType}',
                                style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
                          ],
                        ),
                      ),
                      Text(Formatters.formatIso(e.timestamp), style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
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
