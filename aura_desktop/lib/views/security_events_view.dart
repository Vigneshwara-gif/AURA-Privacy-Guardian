import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../core/utils/formatters.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';

class SecurityEventsView extends StatefulWidget {
  const SecurityEventsView({super.key});

  @override
  State<SecurityEventsView> createState() => _SecurityEventsViewState();
}

class _SecurityEventsViewState extends State<SecurityEventsView> {
  String _selectedSeverity = 'ALL'; // ALL, CRITICAL, HIGH, MEDIUM, LOW, NORMAL
  final TextEditingController _searchCtrl = TextEditingController();

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final timeline = state.timelineEvents;
    final query = _searchCtrl.text.toLowerCase().trim();

    // Filter events
    final filtered = timeline.where((e) {
      final matchesSeverity = _selectedSeverity == 'ALL' || e.severity.toUpperCase() == _selectedSeverity;
      final matchesQuery = query.isEmpty ||
          e.title.toLowerCase().contains(query) ||
          e.summary.toLowerCase().contains(query) ||
          e.entityName.toLowerCase().contains(query) ||
          e.eventType.toLowerCase().contains(query);
      return matchesSeverity && matchesQuery;
    }).toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header & Search Filter Card
          AuraCard(
            title: 'Real-Time Security Event Center',
            icon: Icons.stream_rounded,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _searchCtrl,
                        decoration: InputDecoration(
                          hintText: 'Search events by keyword, process, IP, or type...',
                          prefixIcon: const Icon(Icons.search_rounded, size: 18, color: AuraTheme.textSecondary),
                          filled: true,
                          fillColor: AuraTheme.surfaceElevated,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: const BorderSide(color: AuraTheme.border),
                          ),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        ),
                        onChanged: (_) => setState(() {}),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    const Text('Severity: ', style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary, fontWeight: FontWeight.w600)),
                    _buildSeverityFilter('ALL', 'All Events'),
                    _buildSeverityFilter('CRITICAL', 'Critical'),
                    _buildSeverityFilter('HIGH', 'High'),
                    _buildSeverityFilter('MEDIUM', 'Medium'),
                    _buildSeverityFilter('LOW', 'Low'),
                    _buildSeverityFilter('NORMAL', 'Normal'),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Events Feed
          AuraCard(
            title: 'Security Event Stream (${filtered.length} Events)',
            icon: Icons.list_alt_rounded,
            child: filtered.isEmpty
                ? Container(
                    padding: const EdgeInsets.all(32),
                    alignment: Alignment.center,
                    child: const Text(
                      'No security events match the current filter criteria.',
                      style: TextStyle(color: AuraTheme.textSecondary),
                    ),
                  )
                  : ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: filtered.length,
                    separatorBuilder: (_, index) => const Divider(height: 1, color: AuraTheme.borderSubtle),
                    itemBuilder: (context, i) {
                      final ev = filtered[i];
                      return InkWell(
                        onTap: () => _showEventDetails(context, ev, state),
                        borderRadius: BorderRadius.circular(8),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
                          child: Row(
                            children: [
                              SeverityBadge(severity: ev.severity),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      ev.title,
                                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(ev.summary, style: const TextStyle(fontSize: 12, color: AuraTheme.textSecondary), maxLines: 2, overflow: TextOverflow.ellipsis),
                                    const SizedBox(height: 4),
                                    Row(
                                      children: [
                                        Text('Entity: ${ev.entityName}', style: const TextStyle(fontSize: 11, color: AuraTheme.primaryLight, fontWeight: FontWeight.w600)),
                                        const SizedBox(width: 8),
                                        Text('• Type: ${ev.eventType}', style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 12),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Text(
                                    Formatters.formatIso(ev.timestamp),
                                    style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted),
                                  ),
                                  const SizedBox(height: 4),
                                  const Icon(Icons.arrow_forward_ios_rounded, size: 12, color: AuraTheme.textSecondary),
                                ],
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  void _showEventDetails(BuildContext context, dynamic ev, AuraStateProvider state) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AuraTheme.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: const BorderSide(color: AuraTheme.border)),
        title: Row(
          children: [
            SeverityBadge(severity: ev.severity),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                ev.title,
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(ev.summary, style: const TextStyle(fontSize: 13, color: AuraTheme.textPrimary, height: 1.4)),
              const SizedBox(height: 14),
              const Divider(height: 1, color: AuraTheme.borderSubtle),
              const SizedBox(height: 12),
              _buildDetailField('Entity Target', ev.entityName),
              _buildDetailField('Event Category', ev.eventType),
              _buildDetailField('Recorded Timestamp', Formatters.formatIso(ev.timestamp)),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('CLOSE', style: TextStyle(color: AuraTheme.textSecondary)),
          ),
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(backgroundColor: AuraTheme.primary),
            onPressed: () {
              Navigator.pop(ctx);
              state.navigateTo(8); // Navigate to Incidents
            },
            icon: const Icon(Icons.assignment_outlined, size: 14, color: Colors.white),
            label: const Text('CREATE CASE', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailField(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 140,
            child: Text(label, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary)),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(fontSize: 12, color: AuraTheme.textPrimary, fontFamily: 'monospace')),
          ),
        ],
      ),
    );
  }

  Widget _buildSeverityFilter(String key, String label) {
    final isSelected = _selectedSeverity == key;
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: ChoiceChip(
        label: Text(label, style: TextStyle(fontSize: 11, fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500)),
        selected: isSelected,
        selectedColor: AuraTheme.primary.withValues(alpha: 0.2),
        backgroundColor: AuraTheme.surfaceElevated,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
        onSelected: (_) => setState(() => _selectedSeverity = key),
      ),
    );
  }
}
