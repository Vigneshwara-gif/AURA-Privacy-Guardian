import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';

class ScanView extends StatelessWidget {
  const ScanView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final scan = state.latestScan;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header & Scan CTA
          AuraCard(
            title: '16-Category Full PC Security & Privacy Audit',
            icon: Icons.security_rounded,
            trailing: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: AuraTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              onPressed: state.isScanning ? null : () => state.runFullSecurityScan(),
              icon: state.isScanning
                  ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.play_arrow_rounded, size: 18),
              label: Text(state.isScanning ? 'AUDITING IN PROGRESS...' : 'START FULL AUDIT',
                  style: const TextStyle(fontWeight: FontWeight.w700)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (state.isScanning) ...[
                  LinearProgressIndicator(
                    value: state.scanProgress,
                    minHeight: 6,
                    backgroundColor: AuraTheme.border,
                    valueColor: const AlwaysStoppedAnimation<Color>(AuraTheme.primaryLight),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Executing Checkpoint: ${state.scanCurrentCategory}',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AuraTheme.primaryLight)),
                      Text('${(state.scanProgress * 100).toInt()}%',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary)),
                    ],
                  ),
                  const SizedBox(height: 16),
                ],
                Text(
                  scan != null
                      ? 'Last Full Security Audit (${scan.scanId}) completed in ${scan.durationSeconds.toStringAsFixed(2)}s with ${scan.checksCount} checkpoints evaluated.'
                      : 'No full security scan executed yet. Click above to begin comprehensive inspection.',
                  style: const TextStyle(fontSize: 13, color: AuraTheme.textSecondary),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Audit Scores Summary
          if (scan != null) ...[
            Row(
              children: [
                _ScoreCard(label: 'Security Defense Score', score: scan.overallSecurityScore, icon: Icons.shield_rounded),
                const SizedBox(width: 16),
                _ScoreCard(label: 'Hardware Privacy Score', score: scan.privacyHealthScore, icon: Icons.lock_outline_rounded, isTeal: true),
                const SizedBox(width: 16),
                _ScoreCard(label: 'Composite Risk Index', score: scan.compositeRiskScore, icon: Icons.speed_rounded, isRisk: true),
              ],
            ),
            const SizedBox(height: 24),

            // Narrative Summary
            AuraCard(
              title: 'Executive Scan Narrative',
              icon: Icons.notes_rounded,
              child: Text(
                scan.narrativeSummary,
                style: const TextStyle(fontSize: 13, height: 1.5, color: AuraTheme.textPrimary),
              ),
            ),
            const SizedBox(height: 24),

            // Findings List
            AuraCard(
              title: 'Discovered Findings (${scan.findings.length})',
              icon: Icons.bug_report_rounded,
              child: scan.findings.isEmpty
                  ? const Padding(
                      padding: EdgeInsets.symmetric(vertical: 20),
                      child: Center(
                        child: Text('Zero vulnerabilities or anomalies found. System posture is fully compliant.',
                            style: TextStyle(color: AuraTheme.healthy)),
                      ),
                    )
                  : Column(
                      children: scan.findings.map((f) {
                        return Container(
                          margin: const EdgeInsets.only(bottom: 12),
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
                                  SeverityBadge(severity: f.severity),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(f.title,
                                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: AuraTheme.border,
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(f.category, style: const TextStyle(fontSize: 10, color: AuraTheme.textSecondary)),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Text('Explanation: ${f.explanation}', style: const TextStyle(fontSize: 12, color: AuraTheme.textSecondary)),
                              const SizedBox(height: 4),
                              Text('Recommendation: ${f.recommendation}', style: const TextStyle(fontSize: 12, color: AuraTheme.primaryLight)),
                            ],
                          ),
                        );
                      }).toList(),
                    ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ScoreCard extends StatelessWidget {
  final String label;
  final int score;
  final IconData icon;
  final bool isTeal;
  final bool isRisk;

  const _ScoreCard({required this.label, required this.score, required this.icon, this.isTeal = false, this.isRisk = false});

  @override
  Widget build(BuildContext context) {
    Color col = isTeal ? AuraTheme.accentTeal : (isRisk ? (score < 25 ? AuraTheme.healthy : AuraTheme.critical) : (score >= 80 ? AuraTheme.healthy : AuraTheme.critical));
    return Expanded(
      child: AuraCard(
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: col.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: col, size: 24),
            ),
            const SizedBox(width: 14),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
                Text('$score/100', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: col)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
