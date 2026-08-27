import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';

class ThreatIntelView extends StatelessWidget {
  const ThreatIntelView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final exp = state.aiExplanation;
    final hunts = state.threatHunts;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Reasoning Chain Header
          AuraCard(
            title: 'AI Anomaly Intelligence & Dual-Model Ensemble',
            icon: Icons.psychology_rounded,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _ModelScore(title: 'Isolation Forest Score', score: exp?.isolationForestScore ?? 0.0),
                    const SizedBox(width: 16),
                    _ModelScore(title: 'Local Outlier Factor (LOF)', score: exp?.lofScore ?? 0.0),
                    const SizedBox(width: 16),
                    _ModelScore(title: 'Combined Ensemble Decision', score: exp?.combinedScore ?? 0.0, isCombined: true),
                  ],
                ),
                const SizedBox(height: 16),
                const Divider(height: 1, color: AuraTheme.borderSubtle),
                const SizedBox(height: 16),
                Text(
                  exp?.narrative ?? 'Calculating multi-model behavioral envelope...',
                  style: const TextStyle(fontSize: 13, height: 1.5, color: AuraTheme.textPrimary),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // 10-D Normalized Feature Breakdown
          if (exp != null) ...[
            AuraCard(
              title: 'Explainable Feature Vector (10-D Normalized Envelope)',
              icon: Icons.tune_rounded,
              child: Column(
                children: exp.featureExplanations.map((f) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: Row(
                      children: [
                        SizedBox(
                          width: 180,
                          child: Text(
                            f.featureName.replaceAll('_', ' ').toUpperCase(),
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary),
                          ),
                        ),
                        Expanded(
                          flex: 3,
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: f.observedNormalized.clamp(0.0, 1.0),
                              minHeight: 8,
                              backgroundColor: AuraTheme.border,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                f.isOutlier ? AuraTheme.critical : AuraTheme.primaryLight,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                        SizedBox(
                          width: 120,
                          child: Text(
                            'Raw: ${f.observedRaw.toStringAsFixed(1)}',
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AuraTheme.textPrimary),
                          ),
                        ),
                        Expanded(
                          flex: 4,
                          child: Text(
                            f.explanationText,
                            style: TextStyle(fontSize: 11, color: f.isOutlier ? AuraTheme.critical : AuraTheme.textMuted),
                          ),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 24),
          ],

          // Threat Hunting Multi-Vector Runner
          AuraCard(
            title: 'Multi-Vector Live Threat Hunting Routines',
            icon: Icons.radar_rounded,
            trailing: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: AuraTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              ),
              onPressed: state.isLoading ? null : () => state.runThreatHunts(),
              icon: const Icon(Icons.play_circle_filled_rounded, size: 16),
              label: const Text('RUN HUNTS NOW', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            ),
            child: hunts == null
                ? const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16),
                    child: Center(
                      child: Text('Click "RUN HUNTS NOW" to execute 5 deep threat hunts across memory, network, and registry.',
                          style: TextStyle(color: AuraTheme.textSecondary)),
                    ),
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(hunts.summary, style: const TextStyle(fontSize: 12, color: AuraTheme.textSecondary)),
                      const SizedBox(height: 16),
                      ...hunts.matches.map((m) {
                        return Container(
                          margin: const EdgeInsets.only(bottom: 10),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AuraTheme.surfaceElevated,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AuraTheme.borderSubtle),
                          ),
                          child: Row(
                            children: [
                              SeverityBadge(severity: m.severity),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(m.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
                                    Text('Target: ${m.entity} | Remediation: ${m.suggestedRemediation}',
                                        style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        );
                      }),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}

class _ModelScore extends StatelessWidget {
  final String title;
  final double score;
  final bool isCombined;

  const _ModelScore({required this.title, required this.score, this.isCombined = false});

  @override
  Widget build(BuildContext context) {
    Color col = isCombined ? AuraTheme.primaryLight : AuraTheme.accentIndigo;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AuraTheme.surfaceElevated,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AuraTheme.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
            const SizedBox(height: 6),
            Text(score.toStringAsFixed(2), style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: col)),
          ],
        ),
      ),
    );
  }
}
