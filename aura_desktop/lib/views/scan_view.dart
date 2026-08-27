import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../models/scan.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/metric_gauge.dart';
import '../widgets/severity_badge.dart';

class ScanView extends StatefulWidget {
  const ScanView({super.key});

  @override
  State<ScanView> createState() => _ScanViewState();
}

class _ScanViewState extends State<ScanView> {
  String _selectedSeverityFilter = 'ALL';

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final scan = state.latestScan;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Scan Trigger & Execution Header
          _buildScanHeaderCard(state, scan),
          const SizedBox(height: 24),

          // 2. Scan Results or Pre-Scan Overview
          if (scan != null) ...[
            // Security Overview Gauges
            _buildScanOverviewSection(scan),
            const SizedBox(height: 24),

            // Executive Narrative
            _buildExecutiveNarrativeCard(scan),
            const SizedBox(height: 24),

            // Findings Explorer
            _buildFindingsSection(scan),
            const SizedBox(height: 24),
          ] else if (!state.isScanning) ...[
            // Pre-Scan 9 Categories Breakdown & Honest Boundary
            _buildPreScanCategoriesGrid(),
            const SizedBox(height: 24),
          ],

          // 3. Honest Security Assessment Boundary Card
          _buildHonestBoundaryCard(),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // SCAN HEADER & TRIGGER CARD
  // -------------------------------------------------------------
  Widget _buildScanHeaderCard(AuraStateProvider state, FullScanReport? scan) {
    return AuraCard(
      title: 'Complete Security & Privacy Assessment',
      icon: Icons.radar_rounded,
      trailing: ElevatedButton.icon(
        style: ElevatedButton.styleFrom(
          backgroundColor: AuraTheme.primary,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        onPressed: state.isScanning ? null : () => state.runFullSecurityScan(),
        icon: state.isScanning
            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
            : const Icon(Icons.play_arrow_rounded, size: 18),
        label: Text(
          state.isScanning ? 'CHECKING YOUR PC...' : 'RUN COMPLETE SECURITY CHECK',
          style: const TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.8),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'AURA assesses security posture, hardware privacy access, process trees, network exposure, persistence mechanisms, and behavioural AI anomalies across your Windows PC.',
            style: TextStyle(fontSize: 13, color: AuraTheme.textSecondary, height: 1.4),
          ),
          if (state.isScanning) ...[
            const SizedBox(height: 16),
            LinearProgressIndicator(
              value: state.scanProgress,
              minHeight: 8,
              backgroundColor: AuraTheme.border,
              valueColor: const AlwaysStoppedAnimation<Color>(AuraTheme.primaryLight),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const SizedBox(
                      width: 12,
                      height: 12,
                      child: CircularProgressIndicator(strokeWidth: 2, color: AuraTheme.primaryLight),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Auditing: ${state.scanCurrentCategory}',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.primaryLight),
                    ),
                  ],
                ),
                Text(
                  '${(state.scanProgress * 100).toInt()}% Complete',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary),
                ),
              ],
            ),
          ] else if (scan != null) ...[
            const SizedBox(height: 12),
            Text(
              'Audit ID: ${scan.scanId} • Evaluated ${scan.checksCount} checkpoints in ${scan.durationSeconds.toStringAsFixed(2)}s',
              style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted),
            ),
          ],
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // POST-SCAN OVERVIEW GAUGES & SEVERITY STATS
  // -------------------------------------------------------------
  Widget _buildScanOverviewSection(FullScanReport scan) {
    final criticalCount = scan.findings.where((f) => f.severity == 'CRITICAL').length;
    final highCount = scan.findings.where((f) => f.severity == 'HIGH').length;
    final mediumCount = scan.findings.where((f) => f.severity == 'MEDIUM').length;
    final lowCount = scan.findings.where((f) => f.severity == 'LOW').length;
    final infoCount = scan.findings.where((f) => f.severity == 'INFO' || f.severity == 'NORMAL').length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: AuraCard(
                title: 'Security Health',
                icon: Icons.shield_rounded,
                child: ScoreMetricGauge(
                  label: 'Defense Health',
                  score: scan.overallSecurityScore,
                  subtitle: 'Defender, Firewall, Secure Boot & TPM verified.',
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: AuraCard(
                title: 'Privacy Health',
                icon: Icons.visibility_off_rounded,
                child: ScoreMetricGauge(
                  label: 'Privacy Sentinel',
                  score: scan.privacyHealthScore,
                  color: AuraTheme.accentTeal,
                  subtitle: 'Camera & Microphone hardware consent verified.',
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: AuraCard(
                title: 'Behavioural Risk',
                icon: Icons.speed_rounded,
                child: ScoreMetricGauge(
                  label: 'Composite Risk Index',
                  score: scan.compositeRiskScore,
                  color: scan.compositeRiskScore < 30
                      ? AuraTheme.healthy
                      : scan.compositeRiskScore < 60
                          ? AuraTheme.warning
                          : AuraTheme.critical,
                  subtitle: 'Isolation Forest & LOF anomaly evaluation.',
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Severity Distribution Row
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AuraTheme.surfaceElevated,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: AuraTheme.borderSubtle),
          ),
          child: Row(
            children: [
              const Text(
                'Discovered Findings: ',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary),
              ),
              const SizedBox(width: 12),
              _buildSeverityChip('CRITICAL', criticalCount, AuraTheme.critical),
              _buildSeverityChip('HIGH', highCount, AuraTheme.high),
              _buildSeverityChip('MEDIUM', mediumCount, AuraTheme.medium),
              _buildSeverityChip('LOW', lowCount, AuraTheme.low),
              _buildSeverityChip('INFO', infoCount, AuraTheme.info),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSeverityChip(String label, int count, Color color) {
    return Container(
      margin: const EdgeInsets.only(right: 10),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: count > 0 ? color.withValues(alpha: 0.15) : AuraTheme.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: count > 0 ? color.withValues(alpha: 0.4) : AuraTheme.borderSubtle),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 6, height: 6, decoration: BoxDecoration(shape: BoxShape.circle, color: count > 0 ? color : AuraTheme.textMuted)),
          const SizedBox(width: 6),
          Text(
            '$count $label',
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: count > 0 ? color : AuraTheme.textMuted),
          ),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // EXECUTIVE NARRATIVE
  // -------------------------------------------------------------
  Widget _buildExecutiveNarrativeCard(FullScanReport scan) {
    return AuraCard(
      title: 'Executive Scan Narrative',
      icon: Icons.notes_rounded,
      child: Text(
        scan.narrativeSummary,
        style: const TextStyle(fontSize: 13, height: 1.5, color: AuraTheme.textPrimary),
      ),
    );
  }

  // -------------------------------------------------------------
  // FINDINGS EXPLORER
  // -------------------------------------------------------------
  Widget _buildFindingsSection(FullScanReport scan) {
    final filteredFindings = scan.findings.where((f) {
      if (_selectedSeverityFilter == 'ALL') return true;
      return f.severity.toUpperCase() == _selectedSeverityFilter;
    }).toList();

    return AuraCard(
      title: 'Discovered Findings & Recommendations (${scan.findings.length})',
      icon: Icons.bug_report_rounded,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildFilterButton('ALL', 'All (${scan.findings.length})'),
          _buildFilterButton('CRITICAL', 'Critical'),
          _buildFilterButton('HIGH', 'High'),
          _buildFilterButton('MEDIUM', 'Medium'),
          _buildFilterButton('LOW', 'Low'),
        ],
      ),
      child: filteredFindings.isEmpty
          ? Container(
              padding: const EdgeInsets.all(24),
              alignment: Alignment.center,
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.check_circle_rounded, color: AuraTheme.healthy, size: 20),
                  SizedBox(width: 10),
                  Text('Zero findings match this filter. System security posture is compliant.', style: TextStyle(color: AuraTheme.healthy)),
                ],
              ),
            )
          : ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: filteredFindings.length,
              separatorBuilder: (_, index) => const SizedBox(height: 12),
              itemBuilder: (context, i) {
                final f = filteredFindings[i];
                return _buildFindingDetailCard(f);
              },
            ),
    );
  }

  Widget _buildFilterButton(String key, String label) {
    final isSelected = _selectedSeverityFilter == key;
    return Padding(
      padding: const EdgeInsets.only(left: 6),
      child: InkWell(
        onTap: () => setState(() => _selectedSeverityFilter = key),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: isSelected ? AuraTheme.primary.withValues(alpha: 0.2) : Colors.transparent,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: isSelected ? AuraTheme.primaryLight : AuraTheme.borderSubtle),
          ),
          child: Text(
            label,
            style: TextStyle(fontSize: 10, fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500, color: isSelected ? AuraTheme.primaryLight : AuraTheme.textSecondary),
          ),
        ),
      ),
    );
  }

  Widget _buildFindingDetailCard(SecurityFinding f) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AuraTheme.surfaceElevated,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AuraTheme.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SeverityBadge(severity: f.severity),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  f.title,
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: AuraTheme.border,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(f.category, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: AuraTheme.textSecondary)),
              ),
            ],
          ),
          const SizedBox(height: 12),

          _buildFindingRow('What AURA Found', f.explanation, Icons.search_rounded),
          if (f.recommendation.isNotEmpty) ...[
            const SizedBox(height: 8),
            _buildFindingRow('Recommended Action', f.recommendation, Icons.lightbulb_outline_rounded, isHighlight: true),
          ],
          if (f.affectedEntity.isNotEmpty) ...[
            const SizedBox(height: 8),
            _buildFindingRow('Evidence & Affected Entity', f.affectedEntity, Icons.fingerprint_rounded),
          ],
          const SizedBox(height: 8),
          Row(
            children: [
              Text('Confidence: ${(f.confidence * 100).toInt()}%', style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
              const SizedBox(width: 16),
              Text('Remediation Status: ${f.remediationStatus}', style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildFindingRow(String label, String content, IconData icon, {bool isHighlight = false}) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 14, color: isHighlight ? AuraTheme.primaryLight : AuraTheme.textSecondary),
        const SizedBox(width: 8),
        Text('$label: ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: isHighlight ? AuraTheme.primaryLight : AuraTheme.textSecondary)),
        Expanded(
          child: Text(
            content,
            style: TextStyle(fontSize: 12, color: isHighlight ? AuraTheme.textPrimary : AuraTheme.textSecondary, height: 1.3),
          ),
        ),
      ],
    );
  }

  // -------------------------------------------------------------
  // PRE-SCAN 9 CATEGORIES GRID
  // -------------------------------------------------------------
  Widget _buildPreScanCategoriesGrid() {
    final categories = [
      {'title': 'System Posture', 'desc': 'OS version, kernel build, hardware capacity, and boot stats.', 'icon': Icons.computer_rounded},
      {'title': 'Windows Security Controls', 'desc': 'Windows Defender RTP, Firewall matrix, TPM 2.0, Secure Boot, UAC.', 'icon': Icons.security_rounded},
      {'title': 'Hardware Privacy Sentinels', 'desc': 'Camera & Microphone registry consent and active session indicators.', 'icon': Icons.videocam_rounded},
      {'title': 'Process Execution Trees', 'desc': 'Parent-child hierarchies, elevated processes, and SHA-256 hashes.', 'icon': Icons.account_tree_rounded},
      {'title': 'Network Exposure & Flows', 'desc': 'Listening ports, active socket flows, and remote IP classification.', 'icon': Icons.hub_rounded},
      {'title': 'Persistence Mechanisms', 'desc': 'Registry Run keys, Windows background services, and scheduled tasks.', 'icon': Icons.repeat_rounded},
      {'title': 'Windows Security Events', 'desc': 'Logon failures, security audit logs, and privilege escalations.', 'icon': Icons.stream_rounded},
      {'title': 'Behavioural Baselines', 'desc': 'Process CPU/memory deviation envelopes from nominal baselines.', 'icon': Icons.timeline_rounded},
      {'title': 'AI Anomaly Ensemble', 'desc': 'Dual-model Isolation Forest and Local Outlier Factor (LOF) evaluation.', 'icon': Icons.psychology_rounded},
    ];

    return AuraCard(
      title: 'Assessment Scope (9 Checkpoint Categories)',
      icon: Icons.checklist_rounded,
      child: GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 3,
          childAspectRatio: 2.2,
          crossAxisSpacing: 14,
          mainAxisSpacing: 14,
        ),
        itemCount: categories.length,
        itemBuilder: (context, i) {
          final cat = categories[i];
          return Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AuraTheme.surfaceElevated,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AuraTheme.borderSubtle),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(cat['icon'] as IconData, size: 16, color: AuraTheme.primaryLight),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        cat['title'] as String,
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  cat['desc'] as String,
                  style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  // -------------------------------------------------------------
  // HONEST ASSESSMENT BOUNDARY CARD
  // -------------------------------------------------------------
  Widget _buildHonestBoundaryCard() {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.25),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AuraTheme.borderSubtle),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline_rounded, size: 18, color: AuraTheme.textSecondary),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'AURA Assessment Scope & Methodological Boundary',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                ),
                SizedBox(height: 4),
                Text(
                  'AURA evaluates configuration posture, hardware privacy access, process execution behaviors, socket exposure, and statistical anomalies. AURA is designed to provide visibility and intelligence; it operates alongside your Windows Defender antivirus rather than replacing traditional file-signature scanners.',
                  style: TextStyle(fontSize: 11, color: AuraTheme.textSecondary, height: 1.4),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
