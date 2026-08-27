import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../core/utils/formatters.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/metric_gauge.dart';
import '../widgets/severity_badge.dart';

class OverviewView extends StatelessWidget {
  const OverviewView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final telem = state.telemetry;
    final posture = state.posture;
    final priv = state.privacySummary;
    final scan = state.latestScan;

    final secScore = posture?.overallPostureScore ?? 100;
    final privScore = priv?.overallPrivacyScore ?? 100;
    final compRisk = scan?.compositeRiskScore ?? 10;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // A. Executive Protection Hero Status Banner
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AuraTheme.surfaceElevated,
                  AuraTheme.primary.withValues(alpha: 0.12),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AuraTheme.primary.withValues(alpha: 0.3)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AuraTheme.primary.withValues(alpha: 0.2),
                    shape: BoxShape.circle,
                    border: Border.all(color: AuraTheme.primaryLight.withValues(alpha: 0.5)),
                  ),
                  child: const Icon(Icons.verified_user_rounded, color: AuraTheme.primaryLight, size: 36),
                ),
                const SizedBox(width: 20),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Text(
                            'SYSTEM STATUS: ',
                            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 1.2, color: AuraTheme.textSecondary),
                          ),
                          Text(
                            secScore >= 80 ? 'PROTECTED' : 'ATTENTION REQUIRED',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w800,
                              color: secScore >= 80 ? AuraTheme.healthy : AuraTheme.medium,
                              letterSpacing: 1.0,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        telem != null
                            ? 'Host ${telem.hostname} running ${telem.osDisplayVersion} (${telem.architecture}). Background telemetry active.'
                            : 'Connecting to AURA Local Engine...',
                        style: const TextStyle(fontSize: 13, color: AuraTheme.textPrimary),
                      ),
                    ],
                  ),
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AuraTheme.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onPressed: state.isScanning ? null : () => state.runFullSecurityScan(),
                  icon: const Icon(Icons.shield_rounded, size: 18),
                  label: const Text('RUN FULL SCAN', style: TextStyle(fontWeight: FontWeight.w700)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // B. Tri-Core Score Gauges
          Row(
            children: [
              Expanded(
                child: AuraCard(
                  title: 'Security Posture Health',
                  icon: Icons.health_and_safety_rounded,
                  child: ScoreMetricGauge(
                    label: 'Overall Defense Score',
                    score: secScore,
                    subtitle: 'Defender RTP, Firewall matrix, TPM & Secure Boot verified.',
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: AuraCard(
                  title: 'Hardware Privacy Sentinel',
                  icon: Icons.visibility_off_rounded,
                  child: ScoreMetricGauge(
                    label: 'Privacy Sentinel Score',
                    score: privScore,
                    color: AuraTheme.accentTeal,
                    subtitle: priv != null
                        ? '${priv.camera.deviceCount} Camera(s), ${priv.microphone.deviceCount} Mic(s) monitored.'
                        : 'Querying hardware consent store...',
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: AuraCard(
                  title: 'Composite Risk Rating',
                  icon: Icons.speed_rounded,
                  child: ScoreMetricGauge(
                    label: 'Calculated Risk Index',
                    score: compRisk,
                    color: compRisk < 25 ? AuraTheme.healthy : (compRisk < 50 ? AuraTheme.medium : AuraTheme.critical),
                    subtitle: 'Multi-signal anomaly & threat correlation index.',
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // C. System Telemetry & Posture Row
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // System Health Metrics
              Expanded(
                flex: 3,
                child: AuraCard(
                  title: 'Live System Health & Utilization',
                  icon: Icons.speed_rounded,
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: _MetricTile(
                              label: 'CPU Usage',
                              value: telem != null ? '${telem.cpuPercent.toStringAsFixed(1)}%' : '0.0%',
                              sub: telem != null ? '${telem.logicalCores} Logical Cores' : '',
                              icon: Icons.memory_rounded,
                            ),
                          ),
                          Expanded(
                            child: _MetricTile(
                              label: 'RAM Memory',
                              value: telem != null ? '${telem.memoryPercent.toStringAsFixed(1)}%' : '0.0%',
                              sub: telem != null ? '${Formatters.formatBytes(telem.memoryUsedBytes)} / ${Formatters.formatBytes(telem.memoryTotalBytes)}' : '',
                              icon: Icons.storage_rounded,
                            ),
                          ),
                          Expanded(
                            child: _MetricTile(
                              label: 'Disk Volume (C:)',
                              value: telem != null ? '${telem.diskPercent.toStringAsFixed(1)}%' : '0.0%',
                              sub: telem != null ? '${Formatters.formatBytes(telem.diskUsedBytes)} used' : '',
                              icon: Icons.album_rounded,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      const Divider(height: 1, color: AuraTheme.borderSubtle),
                      const SizedBox(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Host Uptime: ${telem != null ? (telem.uptimeSeconds / 3600).toStringAsFixed(1) : 0} hours',
                              style: const TextStyle(fontSize: 12, color: AuraTheme.textSecondary)),
                          Text('Build: ${telem?.osBuild ?? "N/A"}',
                              style: const TextStyle(fontSize: 12, color: AuraTheme.textSecondary)),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 16),

              // Security Posture Highlights
              Expanded(
                flex: 2,
                child: AuraCard(
                  title: 'Windows Security Posture',
                  icon: Icons.admin_panel_settings_rounded,
                  child: Column(
                    children: [
                      _PostureRow(
                        title: 'Windows Defender Antivirus',
                        status: posture?.defender.antivirusEnabled == true,
                      ),
                      const SizedBox(height: 10),
                      _PostureRow(
                        title: 'Real-Time Protection',
                        status: posture?.defender.realtimeProtectionEnabled == true,
                      ),
                      const SizedBox(height: 10),
                      _PostureRow(
                        title: 'Windows Defender Firewall',
                        status: posture?.firewall.allProfilesSecure == true,
                      ),
                      const SizedBox(height: 10),
                      _PostureRow(
                        title: 'UEFI Secure Boot',
                        status: posture?.secureBootEnabled == true,
                      ),
                      const SizedBox(height: 10),
                      _PostureRow(
                        title: 'TPM Security Module',
                        status: posture?.tpmPresent == true,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // D. Live Security Timeline & Findings Stream
          AuraCard(
            title: 'Recent Security Findings & Events',
            icon: Icons.notifications_active_rounded,
            child: state.findings.isEmpty
                ? const Padding(
                    padding: EdgeInsets.symmetric(vertical: 24),
                    child: Center(
                      child: Text(
                        'Zero active security threats. Host is operating within nominal baseline.',
                        style: TextStyle(color: AuraTheme.textSecondary),
                      ),
                    ),
                  )
                : Column(
                    children: state.findings.take(5).map((f) {
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
                            SeverityBadge(severity: f.severity),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    f.title,
                                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                                  ),
                                  Text(
                                    f.explanation,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary),
                                  ),
                                ],
                              ),
                            ),
                            Text(
                              Formatters.formatTimeOnly(f.timestamp),
                              style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted),
                            ),
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

class _MetricTile extends StatelessWidget {
  final String label;
  final String value;
  final String sub;
  final IconData icon;

  const _MetricTile({required this.label, required this.value, required this.sub, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
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
              Icon(icon, size: 14, color: AuraTheme.primaryLight),
              const SizedBox(width: 6),
              Text(label, style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
            ],
          ),
          const SizedBox(height: 8),
          Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AuraTheme.textPrimary)),
          if (sub.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(sub, style: const TextStyle(fontSize: 10, color: AuraTheme.textMuted)),
          ],
        ],
      ),
    );
  }
}

class _PostureRow extends StatelessWidget {
  final String title;
  final bool status;

  const _PostureRow({required this.title, required this.status});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(
          status ? Icons.check_circle_rounded : Icons.cancel_rounded,
          size: 16,
          color: status ? AuraTheme.healthy : AuraTheme.critical,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(title, style: const TextStyle(fontSize: 12, color: AuraTheme.textPrimary)),
        ),
        Text(
          status ? 'ENABLED' : 'INACTIVE',
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: status ? AuraTheme.healthy : AuraTheme.critical,
          ),
        ),
      ],
    );
  }
}
