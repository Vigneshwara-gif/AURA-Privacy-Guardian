import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../core/utils/formatters.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';

class ReportsView extends StatelessWidget {
  const ReportsView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final report = state.latestReport;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AuraCard(
            title: 'Security Audit & Technical Report Generator',
            icon: Icons.assessment_rounded,
            trailing: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: AuraTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              ),
              onPressed: state.isLoading ? null : () => state.generateReport(),
              icon: const Icon(Icons.note_add_rounded, size: 16),
              label: const Text('GENERATE AUDIT REPORT', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            ),
            child: Text(
              'Compiles executive summary, defense posture, hardware privacy health, persistence matrix, and active findings into an audit document.',
              style: const TextStyle(fontSize: 13, color: AuraTheme.textSecondary),
            ),
          ),
          const SizedBox(height: 24),

          if (report == null)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(
                child: Text('Click "GENERATE AUDIT REPORT" to compile live system audit.', style: TextStyle(color: AuraTheme.textSecondary)),
              ),
            )
          else ...[
            AuraCard(
              title: 'Report: ${report.reportId} (${report.hostname})',
              icon: Icons.description_rounded,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Generated: ${Formatters.formatIso(report.generatedAt)}', style: const TextStyle(fontSize: 12, color: AuraTheme.textMuted)),
                      Text('Risk Rating: ${report.compositeRiskScore}/100 (${report.riskLevel})',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                            color: report.compositeRiskScore < 25 ? AuraTheme.healthy : AuraTheme.critical,
                          )),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text('Executive Summary', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AuraTheme.primaryLight)),
                  const SizedBox(height: 6),
                  Text(report.executiveSummary, style: const TextStyle(fontSize: 13, height: 1.5, color: AuraTheme.textPrimary)),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      _ReportScoreBox(title: 'Security Defense Score', score: report.overallSecurityScore),
                      const SizedBox(width: 12),
                      _ReportScoreBox(title: 'Hardware Privacy Score', score: report.privacyHealthScore, isTeal: true),
                      const SizedBox(width: 12),
                      _ReportScoreBox(title: 'Composite Risk Rating', score: report.compositeRiskScore, isRisk: true),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ReportScoreBox extends StatelessWidget {
  final String title;
  final int score;
  final bool isTeal;
  final bool isRisk;

  const _ReportScoreBox({required this.title, required this.score, this.isTeal = false, this.isRisk = false});

  @override
  Widget build(BuildContext context) {
    Color col = isTeal ? AuraTheme.accentTeal : (isRisk ? (score < 25 ? AuraTheme.healthy : AuraTheme.critical) : (score >= 80 ? AuraTheme.healthy : AuraTheme.critical));
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AuraTheme.surfaceElevated,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: AuraTheme.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 10, color: AuraTheme.textSecondary)),
            const SizedBox(height: 4),
            Text('$score/100', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: col)),
          ],
        ),
      ),
    );
  }
}
