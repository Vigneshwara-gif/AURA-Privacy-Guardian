import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../core/utils/formatters.dart';
import '../models/incident.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';
import '../widgets/aura_status_badge.dart';
import '../widgets/aura_empty_state.dart';

class IncidentsView extends StatefulWidget {
  const IncidentsView({super.key});

  @override
  State<IncidentsView> createState() => _IncidentsViewState();
}

class _IncidentsViewState extends State<IncidentsView> {
  String _lifecycleFilter = 'ALL';

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final incidents = state.incidents;

    var filtered = incidents;
    if (_lifecycleFilter != 'ALL') {
      filtered = incidents.where((i) => i.state.toUpperCase() == _lifecycleFilter).toList();
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Header Banner
          AuraCard(
            title: 'Security Incident Studio & Case Management',
            icon: Icons.emergency_rounded,
            trailing: TextButton.icon(
              onPressed: () => state.refreshAllData(),
              icon: const Icon(Icons.refresh_rounded, size: 14),
              label: const Text('REFRESH CASES', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Manage and triage multi-signal security incidents on your Windows PC through a structured lifecycle: NEW ➔ INVESTIGATING ➔ ACKNOWLEDGED ➔ CONTAINED ➔ RESOLVED.',
                  style: TextStyle(fontSize: 13, color: AuraTheme.textSecondary, height: 1.4),
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: ['ALL', 'NEW', 'INVESTIGATING', 'ACKNOWLEDGED', 'CONTAINED', 'RESOLVED', 'FALSE_POSITIVE'].map((lifecycle) {
                    final isSel = _lifecycleFilter == lifecycle;
                    return ChoiceChip(
                      label: Text(
                        lifecycle.replaceAll('_', ' '),
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          color: isSel ? Colors.black : AuraTheme.textSecondary,
                        ),
                      ),
                      selected: isSel,
                      selectedColor: AuraTheme.primaryLight,
                      backgroundColor: AuraTheme.surfaceElevated,
                      onSelected: (_) => setState(() => _lifecycleFilter = lifecycle),
                    );
                  }).toList(),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // 2. Incident Cases List
          if (filtered.isEmpty)
            AuraEmptyState(
              icon: Icons.verified_user_rounded,
              title: 'Zero Active Incidents in Filter',
              description: 'No security incidents currently match the selected lifecycle criteria.',
              actionLabel: 'SHOW ALL CASES',
              onAction: () => setState(() => _lifecycleFilter = 'ALL'),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: filtered.length,
              separatorBuilder: (_, index) => const SizedBox(height: 16),
              itemBuilder: (context, i) {
                final inc = filtered[i];
                return _buildIncidentCard(context, inc, state);
              },
            ),
        ],
      ),
    );
  }

  Widget _buildIncidentCard(BuildContext context, IncidentItem inc, AuraStateProvider state) {
    return Container(
      decoration: BoxDecoration(
        color: AuraTheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AuraTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Incident Header Bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                SeverityBadge(severity: inc.severity),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'CASE ${inc.incidentId}: ${inc.title}',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: AuraTheme.textPrimary),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Created: ${Formatters.formatIso(inc.createdAt)} • Updated: ${Formatters.formatIso(inc.updatedAt)}',
                        style: const TextStyle(fontSize: 10, color: AuraTheme.textSecondary),
                      ),
                    ],
                  ),
                ),
                AuraStatusBadge(status: inc.state, fontSize: 11),
              ],
            ),
          ),
          const Divider(height: 1, color: AuraTheme.borderSubtle),

          // Body Content
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  inc.summary,
                  style: const TextStyle(fontSize: 13, color: AuraTheme.textPrimary, height: 1.4),
                ),
                const SizedBox(height: 14),

                // Affected Entities with Drilldowns
                if (inc.affectedEntities.isNotEmpty) ...[
                  const Text('AFFECTED ENTITIES & CORRELATED TARGETS:', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: AuraTheme.primaryLight, letterSpacing: 0.8)),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: inc.affectedEntities.map((ent) {
                      final isPid = int.tryParse(ent) != null || ent.startsWith('PID:');
                      final isIp = ent.contains('.') && ent.split('.').length == 4;

                      return ActionChip(
                        avatar: Icon(
                          isPid ? Icons.memory_rounded : isIp ? Icons.language_rounded : Icons.label_outline_rounded,
                          size: 12,
                          color: AuraTheme.primaryLight,
                        ),
                        label: Text(ent, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
                        backgroundColor: AuraTheme.surfaceElevated,
                        side: const BorderSide(color: AuraTheme.borderSubtle),
                        onPressed: () {
                          if (isPid) {
                            final pidNum = int.tryParse(ent.replaceAll('PID:', '').trim());
                            if (pidNum != null) state.navigateTo(4, targetPid: pidNum);
                          } else if (isIp) {
                            state.navigateTo(5, targetIp: ent);
                          }
                        },
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 16),
                ],

                // Lifecycle Transition Buttons
                Row(
                  children: [
                    const Text('TRANSITION STATE: ', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: AuraTheme.textSecondary, letterSpacing: 0.6)),
                    const SizedBox(width: 8),
                    _buildLifecycleButton(inc.incidentId, 'INVESTIGATING', inc.state, state, AuraTheme.primaryLight),
                    const SizedBox(width: 6),
                    _buildLifecycleButton(inc.incidentId, 'CONTAINED', inc.state, state, AuraTheme.warning),
                    const SizedBox(width: 6),
                    _buildLifecycleButton(inc.incidentId, 'RESOLVED', inc.state, state, AuraTheme.healthy),
                    const SizedBox(width: 6),
                    _buildLifecycleButton(inc.incidentId, 'FALSE_POSITIVE', inc.state, state, AuraTheme.textSecondary),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLifecycleButton(String incidentId, String targetState, String currentState, AuraStateProvider state, Color color) {
    final isCurrent = currentState.toUpperCase() == targetState.toUpperCase();

    return OutlinedButton(
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        minimumSize: Size.zero,
        side: BorderSide(color: isCurrent ? color : AuraTheme.border),
        backgroundColor: isCurrent ? color.withValues(alpha: 0.12) : Colors.transparent,
      ),
      onPressed: isCurrent ? null : () => state.updateIncidentState(incidentId, targetState),
      child: Text(
        targetState.replaceAll('_', ' '),
        style: TextStyle(
          fontSize: 10,
          fontWeight: isCurrent ? FontWeight.w800 : FontWeight.w600,
          color: isCurrent ? color : AuraTheme.textSecondary,
        ),
      ),
    );
  }
}
