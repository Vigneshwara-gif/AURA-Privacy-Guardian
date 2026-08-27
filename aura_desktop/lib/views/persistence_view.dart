import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';

class PersistenceView extends StatelessWidget {
  const PersistenceView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final pers = state.persistence;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Summary Card
          AuraCard(
            title: 'Auto-Start & Persistence Intelligence Engine',
            icon: Icons.repeat_rounded,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _PersStat(title: 'Startup Applications', value: '${pers?.totalStartupApps ?? 0}'),
                    const SizedBox(width: 12),
                    _PersStat(title: 'Windows Services', value: '${pers?.totalServices ?? 0}'),
                    const SizedBox(width: 12),
                    _PersStat(title: 'Scheduled Tasks', value: '${pers?.totalScheduledTasks ?? 0}'),
                    const SizedBox(width: 12),
                    _PersStat(title: 'Suspicious Locations', value: '${pers?.suspiciousCount ?? 0}', isAlert: (pers?.suspiciousCount ?? 0) > 0),
                  ],
                ),
                const SizedBox(height: 16),
                Text(pers?.summary ?? 'Analyzing persistence mechanisms...', style: const TextStyle(fontSize: 12, color: AuraTheme.textSecondary)),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Analyzed Persistence Items
          AuraCard(
            title: 'Evaluated Auto-Start Entries',
            icon: Icons.checklist_rounded,
            child: (pers?.analyzedItems.isEmpty ?? true)
                ? const Text('No persistence entries loaded.')
                : Column(
                    children: pers!.analyzedItems.map((item) {
                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AuraTheme.surfaceElevated,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: item.isSuspiciousLocation ? AuraTheme.critical : AuraTheme.borderSubtle),
                        ),
                        child: Row(
                          children: [
                            SeverityBadge(severity: item.riskSeverity, compact: true),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(item.name, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
                                  Text('${item.itemType} | Path: ${item.executablePath ?? "Unknown"}',
                                      style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
                                ],
                              ),
                            ),
                            Text(item.locationOrTrigger, style: const TextStyle(fontSize: 10, color: AuraTheme.textMuted)),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
          ),
        ],
      ),
    );
  }
}

class _PersStat extends StatelessWidget {
  final String title;
  final String value;
  final bool isAlert;

  const _PersStat({required this.title, required this.value, this.isAlert = false});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AuraTheme.surfaceElevated,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: isAlert ? AuraTheme.critical : AuraTheme.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 10, color: AuraTheme.textSecondary)),
            const SizedBox(height: 4),
            Text(value,
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: isAlert ? AuraTheme.critical : AuraTheme.textPrimary,
                )),
          ],
        ),
      ),
    );
  }
}
