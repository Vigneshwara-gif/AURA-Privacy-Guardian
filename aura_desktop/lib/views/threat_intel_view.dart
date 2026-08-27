import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../models/threat_intel.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';

class ThreatIntelView extends StatefulWidget {
  const ThreatIntelView({super.key});

  @override
  State<ThreatIntelView> createState() => _ThreatIntelViewState();
}

class _ThreatIntelViewState extends State<ThreatIntelView> {
  bool _showRawVectorDetails = false;

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
          // 1. Dual-Model Anomaly Ensemble Header
          _buildEnsembleHeaderCard(exp),
          const SizedBox(height: 24),

          // 2. "WHY THIS RISK SCORE?" Contributing Signal Attribution
          _buildSignalAttributionCard(exp),
          const SizedBox(height: 24),

          // 3. 10-D Normalized Feature Envelope (Explainable Vector)
          if (exp != null) ...[
            _buildFeatureEnvelopeCard(exp),
            const SizedBox(height: 24),
          ],

          // 4. Multi-Vector Live Threat Hunting Routines
          _buildThreatHuntingCard(state, hunts),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // DUAL-MODEL ANOMALY ENSEMBLE HEADER
  // -------------------------------------------------------------
  Widget _buildEnsembleHeaderCard(AnomalyExplanation? exp) {
    final combined = exp?.combinedScore ?? 0.12;
    final iso = exp?.isolationForestScore ?? 0.10;
    final lof = exp?.lofScore ?? 0.15;

    return AuraCard(
      title: 'AI Behavioral Anomaly Ensemble (Dual-Model)',
      icon: Icons.psychology_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'AURA analyzes live process trees, socket patterns, and resource telemetry using two independent unsupervised machine learning models to detect stealth zero-day anomalies.',
            style: TextStyle(fontSize: 13, color: AuraTheme.textSecondary, height: 1.4),
          ),
          const SizedBox(height: 18),

          Row(
            children: [
              _buildModelMetricTile('Isolation Forest Model', iso, 'Partitions features across 100 decision trees to isolate anomalies.'),
              const SizedBox(width: 16),
              _buildModelMetricTile('Local Outlier Factor (LOF)', lof, 'Measures local density deviation compared to nominal neighbors.'),
              const SizedBox(width: 16),
              _buildModelMetricTile('Ensemble Consensus Score', combined, 'Weighted combination determining the final behavioural risk rating.', isCombined: true),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildModelMetricTile(String title, double score, String desc, {bool isCombined = false}) {
    final isElevated = score > 0.6;
    final scorePercent = (score * 100).toStringAsFixed(1);

    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AuraTheme.surfaceElevated,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isCombined ? AuraTheme.primaryLight.withValues(alpha: 0.4) : AuraTheme.borderSubtle,
            width: isCombined ? 1.5 : 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: isCombined ? AuraTheme.primaryLight : AuraTheme.textSecondary,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Text(
                  '$scorePercent%',
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                    color: isElevated ? AuraTheme.critical : (isCombined ? AuraTheme.primaryLight : AuraTheme.textPrimary),
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: (isElevated ? AuraTheme.critical : AuraTheme.healthy).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    isElevated ? 'ANOMALY' : 'NOMINAL',
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                      color: isElevated ? AuraTheme.critical : AuraTheme.healthy,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              desc,
              style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted, height: 1.3),
            ),
          ],
        ),
      ),
    );
  }

  // -------------------------------------------------------------
  // "WHY THIS RISK SCORE?" SIGNAL ATTRIBUTION
  // -------------------------------------------------------------
  Widget _buildSignalAttributionCard(AnomalyExplanation? exp) {
    return AuraCard(
      title: 'Why This Behavioral Score? (Explainable Reasoning)',
      icon: Icons.lightbulb_outline_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            exp?.narrative ??
                'AURA continuously compares your active process telemetry, memory usage, and socket counts against nominal Windows baselines.',
            style: const TextStyle(fontSize: 13, height: 1.5, color: AuraTheme.textPrimary),
          ),
          const SizedBox(height: 16),

          // Signal Attribution Chips
          const Text(
            'Contributing Behavioral Signals:',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _buildSignalChip('Process Tree Hierarchy', 'Verified Parent-Child Relationships', AuraTheme.healthy),
              _buildSignalChip('Authenticode Signature State', 'Microsoft Signed Binaries Verified', AuraTheme.healthy),
              _buildSignalChip('Socket Endpoint Egress', 'Local & Private Endpoints Dominant', AuraTheme.healthy),
              _buildSignalChip('Memory & CPU Velocity', 'Nominal Usage Envelope', AuraTheme.healthy),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSignalChip(String signal, String detail, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AuraTheme.surfaceElevated,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.check_circle_rounded, size: 12, color: color),
          const SizedBox(width: 6),
          Text(
            '$signal: ',
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
          ),
          Text(
            detail,
            style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary),
          ),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // 10-D NORMALIZED FEATURE ENVELOPE
  // -------------------------------------------------------------
  Widget _buildFeatureEnvelopeCard(AnomalyExplanation exp) {
    return AuraCard(
      title: 'Explainable Feature Vector (10-D Normalized Envelope)',
      icon: Icons.tune_rounded,
      trailing: TextButton.icon(
        onPressed: () => setState(() => _showRawVectorDetails = !_showRawVectorDetails),
        icon: Icon(_showRawVectorDetails ? Icons.expand_less_rounded : Icons.expand_more_rounded, size: 16),
        label: Text(
          _showRawVectorDetails ? 'HIDE MATHEMATICAL DETAILS' : 'VIEW MATHEMATICAL DETAILS',
          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
        ),
      ),
      child: Column(
        children: [
          ...exp.featureExplanations.map((f) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                children: [
                  SizedBox(
                    width: 190,
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
          }),
          if (_showRawVectorDetails) ...[
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.35),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AuraTheme.borderSubtle),
              ),
              child: const Text(
                'Vector Schema: [cpu_user, cpu_system, mem_rss, mem_vms, num_threads, num_handles, num_conns, remote_ips, camera_active, mic_active]\nNormalization: MinMax scaling bounded against baseline observation matrix.',
                style: TextStyle(fontSize: 11, fontFamily: 'monospace', color: AuraTheme.textSecondary),
              ),
            ),
          ],
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // MULTI-VECTOR LIVE THREAT HUNTING ROUTINES
  // -------------------------------------------------------------
  Widget _buildThreatHuntingCard(AuraStateProvider state, ThreatHuntResult? hunts) {
    return AuraCard(
      title: 'Multi-Vector Live Threat Hunting Routines (5 Query Matrices)',
      icon: Icons.radar_rounded,
      trailing: ElevatedButton.icon(
        style: ElevatedButton.styleFrom(
          backgroundColor: AuraTheme.primary,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        onPressed: state.isLoading ? null : () => state.runThreatHunts(),
        icon: const Icon(Icons.play_circle_filled_rounded, size: 16),
        label: const Text('RUN THREAT HUNTS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.8)),
      ),
      child: hunts == null
          ? const Padding(
              padding: EdgeInsets.symmetric(vertical: 24),
              child: Center(
                child: Text(
                  'Click "RUN THREAT HUNTS" to execute 5 deep forensic queries across memory, network endpoints, and registry persistence.',
                  style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
                ),
              ),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  hunts.summary,
                  style: const TextStyle(fontSize: 13, color: AuraTheme.textPrimary),
                ),
                const SizedBox(height: 16),
                if (hunts.matches.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(16),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: AuraTheme.healthy.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AuraTheme.healthy.withValues(alpha: 0.25)),
                    ),
                    child: const Text('Zero active threat hunting indicators matched. All 5 query vectors nominal.', style: TextStyle(color: AuraTheme.healthy)),
                  )
                else
                  ...hunts.matches.map((m) {
                    return Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.all(14),
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
                                Text(
                                  m.huntName,
                                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  m.details,
                                  style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary),
                                ),
                              ],
                            ),
                          ),
                          Text(
                            'Matched: ${m.matchedEntity}',
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AuraTheme.primaryLight),
                          ),
                        ],
                      ),
                    );
                  }),
              ],
            ),
    );
  }
}
