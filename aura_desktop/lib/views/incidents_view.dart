import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../core/utils/formatters.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';

class IncidentsView extends StatelessWidget {
  const IncidentsView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final incidents = state.incidents;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AuraCard(
            title: 'Security Incident Studio & Case Management',
            icon: Icons.emergency_rounded,
            child: Text(
              'Tracks multi-signal security incidents across lifecycle states: NEW -> INVESTIGATING -> ACKNOWLEDGED -> CONTAINED -> RESOLVED.',
              style: const TextStyle(fontSize: 13, color: AuraTheme.textSecondary),
            ),
          ),
          const SizedBox(height: 24),

          if (incidents.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(
                child: Text('Zero active security incidents. System operating nominal.', style: TextStyle(color: AuraTheme.healthy)),
              ),
            )
          else
            ...incidents.map((inc) {
              return Container(
                margin: const EdgeInsets.only(bottom: 16),
                child: AuraCard(
                  title: '${inc.incidentId}: ${inc.title}',
                  icon: Icons.shield_outlined,
                  trailing: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: AuraTheme.primary.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: AuraTheme.primaryLight.withValues(alpha: 0.4)),
                    ),
                    child: Text(inc.state, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AuraTheme.primaryLight)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          SeverityBadge(severity: inc.severity),
                          const SizedBox(width: 12),
                          Text('Created: ${Formatters.formatIso(inc.createdAt)}', style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Text(inc.summary, style: const TextStyle(fontSize: 13, color: AuraTheme.textPrimary)),
                      const SizedBox(height: 12),
                      const Text('Affected Entities:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary)),
                      const SizedBox(height: 4),
                      Text(inc.affectedEntities.join(', '), style: const TextStyle(fontSize: 12, color: AuraTheme.textMuted)),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          const Text('Transition Lifecycle: ', style: TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
                          const SizedBox(width: 8),
                          OutlinedButton(
                            onPressed: () => state.updateIncidentState(inc.incidentId, 'INVESTIGATING'),
                            child: const Text('INVESTIGATING', style: TextStyle(fontSize: 10)),
                          ),
                          const SizedBox(width: 8),
                          OutlinedButton(
                            onPressed: () => state.updateIncidentState(inc.incidentId, 'RESOLVED'),
                            child: const Text('RESOLVE', style: TextStyle(fontSize: 10, color: AuraTheme.healthy)),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }
}
