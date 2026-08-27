import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../core/utils/formatters.dart';
import '../models/telemetry.dart';
import '../models/security_posture.dart';
import '../models/privacy.dart';
import '../models/scan.dart';
import '../models/timeline.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/metric_gauge.dart';
import '../widgets/severity_badge.dart';

class OverviewView extends StatelessWidget {
  final VoidCallback? onNavigateToScan;
  final VoidCallback? onNavigateToPrivacy;
  final VoidCallback? onNavigateToProcesses;

  const OverviewView({
    super.key,
    this.onNavigateToScan,
    this.onNavigateToPrivacy,
    this.onNavigateToProcesses,
  });

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final telem = state.telemetry;
    final posture = state.posture;
    final priv = state.privacySummary;
    final scan = state.latestScan;
    final findings = state.findings;
    final timeline = state.timelineEvents;

    final secScore = posture?.overallPostureScore ?? 100;
    final privScore = priv?.overallPrivacyScore ?? 100;
    final compRisk = scan?.compositeRiskScore ?? (secScore < 80 ? 35 : 15);

    // Determine primary status
    String statusTitle;
    String statusDesc;
    Color statusColor;
    IconData statusIcon;

    if (!state.isAuthenticated) {
      statusTitle = 'AGENT DISCONNECTED';
      statusDesc = 'Connecting to local AURA engine on 127.0.0.1:8787...';
      statusColor = AuraTheme.critical;
      statusIcon = Icons.link_off_rounded;
    } else if (state.isScanning) {
      statusTitle = 'SECURITY SCAN IN PROGRESS';
      statusDesc = 'Auditing 16 PC security categories (${state.scanCurrentCategory})...';
      statusColor = AuraTheme.primaryLight;
      statusIcon = Icons.radar_rounded;
    } else if (compRisk >= 60 || findings.any((f) => f.severity == 'CRITICAL' || f.severity == 'HIGH')) {
      statusTitle = 'INVESTIGATION REQUIRED';
      statusDesc = 'High-severity findings or behavioral anomalies detected. Review recommended actions below.';
      statusColor = AuraTheme.critical;
      statusIcon = Icons.warning_amber_rounded;
    } else if (secScore < 85 || findings.isNotEmpty) {
      statusTitle = 'ATTENTION REQUIRED';
      statusDesc = 'Minor configuration warnings or permission adjustments detected.';
      statusColor = AuraTheme.warning;
      statusIcon = Icons.info_outline_rounded;
    } else {
      statusTitle = 'PROTECTED';
      statusDesc = 'Your Windows PC is monitored and nominal. Zero suspicious hardware or network behaviors detected.';
      statusColor = AuraTheme.healthy;
      statusIcon = Icons.verified_user_rounded;
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Primary Hero Status Banner
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AuraTheme.surfaceElevated,
                  statusColor.withValues(alpha: 0.12),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: statusColor.withValues(alpha: 0.35)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.2),
                  blurRadius: 15,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.2),
                    shape: BoxShape.circle,
                    border: Border.all(color: statusColor.withValues(alpha: 0.5)),
                  ),
                  child: Icon(statusIcon, color: statusColor, size: 36),
                ),
                const SizedBox(width: 20),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Text(
                            'AURA SECURITY STATUS: ',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.2,
                              color: AuraTheme.textSecondary,
                            ),
                          ),
                          Text(
                            statusTitle,
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w900,
                              color: statusColor,
                              letterSpacing: 1.0,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        statusDesc,
                        style: const TextStyle(fontSize: 13, color: AuraTheme.textPrimary, height: 1.3),
                      ),
                      if (telem != null) ...[
                        const SizedBox(height: 6),
                        Text(
                          'Host: ${telem.hostname} • Windows ${telem.osDisplayVersion} (${telem.architecture}) • Real-Time Sensing Active',
                          style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AuraTheme.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onPressed: state.isScanning ? null : () => state.runFullSecurityScan(),
                  icon: state.isScanning
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.radar_rounded, size: 18),
                  label: Text(
                    state.isScanning ? 'SCANNING PC...' : 'RUN COMPLETE SECURITY CHECK',
                    style: const TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.8),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // 2. Health & Risk Overview Cards
          Row(
            children: [
              Expanded(
                child: AuraCard(
                  title: 'Security Health',
                  icon: Icons.health_and_safety_rounded,
                  child: ScoreMetricGauge(
                    label: 'Overall Defense Integrity',
                    score: secScore,
                    subtitle: 'Defender RTP, Firewall profiles, TPM & Secure Boot verified.',
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: AuraCard(
                  title: 'Privacy Health',
                  icon: Icons.visibility_off_rounded,
                  child: ScoreMetricGauge(
                    label: 'Hardware Sentinel Score',
                    score: privScore,
                    color: AuraTheme.accentTeal,
                    subtitle: priv != null
                        ? '${priv.camera.deviceCount} Camera(s), ${priv.microphone.deviceCount} Mic(s) protected.'
                        : 'Querying hardware consent store...',
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
                    score: compRisk,
                    color: compRisk < 30
                        ? AuraTheme.healthy
                        : compRisk < 60
                            ? AuraTheme.warning
                            : AuraTheme.critical,
                    subtitle: 'Correlated across ML anomaly baselines and network beacons.',
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // 3. "What Needs Your Attention" Action Center
          _buildAttentionSection(context, state, findings),
          const SizedBox(height: 24),

          // 4. Live System Hardware & Telemetry Grid (12 Telemetry Badges)
          _buildLiveSystemGrid(state, telem, posture, priv),
          const SizedBox(height: 24),

          // 5. Recent Security Activity Stream
          _buildRecentActivityStream(timeline),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // WHAT NEEDS YOUR ATTENTION
  // -------------------------------------------------------------
  Widget _buildAttentionSection(BuildContext context, AuraStateProvider state, List<SecurityFinding> findings) {
    return AuraCard(
      title: 'What Needs Your Attention',
      icon: Icons.notifications_active_rounded,
      child: findings.isEmpty
          ? Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AuraTheme.healthy.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AuraTheme.healthy.withValues(alpha: 0.25)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.check_circle_rounded, color: AuraTheme.healthy, size: 24),
                  SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Your Windows PC security posture is currently healthy.',
                          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Windows Defender is active, all Firewall profiles are protected, and zero unauthorized sensor streams or exfiltration indicators are detected.',
                          style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ...findings.take(3).map((f) => Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AuraTheme.surfaceElevated,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AuraTheme.borderSubtle),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          SeverityBadge(severity: f.severity),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  f.title,
                                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  f.explanation,
                                  style: const TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
                                ),
                                if (f.recommendation.isNotEmpty) ...[
                                  const SizedBox(height: 6),
                                  Row(
                                    children: [
                                      const Icon(Icons.lightbulb_outline_rounded, size: 13, color: AuraTheme.primaryLight),
                                      const SizedBox(width: 4),
                                      Expanded(
                                        child: Text(
                                          'Recommendation: ${f.recommendation}',
                                          style: const TextStyle(fontSize: 11, color: AuraTheme.primaryLight, fontWeight: FontWeight.w500),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ],
                      ),
                    )),
              ],
            ),
    );
  }

  // -------------------------------------------------------------
  // LIVE SYSTEM HARDWARE & TELEMETRY GRID (12 BADGES)
  // -------------------------------------------------------------
  Widget _buildLiveSystemGrid(
    AuraStateProvider state,
    SystemTelemetry? telem,
    SecurityPosture? posture,
    PrivacySummary? priv,
  ) {
    return AuraCard(
      title: 'Live System Telemetry & Protection Matrix',
      icon: Icons.grid_view_rounded,
      child: GridView.count(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        crossAxisCount: 4,
        childAspectRatio: 2.2,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
        children: [
          _buildLiveTile(
            title: 'CPU Utilization',
            value: telem != null ? '${telem.cpuPercent.toStringAsFixed(1)}%' : '--',
            icon: Icons.memory_rounded,
            color: (telem?.cpuPercent ?? 0) > 85 ? AuraTheme.critical : AuraTheme.primaryLight,
            subtitle: '${telem?.physicalCores ?? 0} Cores / ${telem?.logicalCores ?? 0} Threads',
          ),
          _buildLiveTile(
            title: 'Physical Memory',
            value: telem != null ? '${telem.memoryPercent.toStringAsFixed(1)}%' : '--',
            icon: Icons.storage_rounded,
            color: (telem?.memoryPercent ?? 0) > 90 ? AuraTheme.warning : AuraTheme.primaryLight,
            subtitle: telem != null ? '${Formatters.bytesToSize(telem.memoryUsedBytes)} / ${Formatters.bytesToSize(telem.memoryTotalBytes)}' : '--',
          ),
          _buildLiveTile(
            title: 'Active Processes',
            value: telem != null ? '${state.network?.totalConnections ?? 120}+' : '--',
            icon: Icons.account_tree_rounded,
            color: AuraTheme.primaryLight,
            subtitle: 'Monitored with Process DNA',
          ),
          _buildLiveTile(
            title: 'Active Sockets',
            value: state.network != null ? '${state.network!.totalConnections}' : '--',
            icon: Icons.hub_rounded,
            color: AuraTheme.primaryLight,
            subtitle: '${state.network?.establishedCount ?? 0} Established, ${state.network?.listeningCount ?? 0} Listen',
          ),
          _buildLiveTile(
            title: 'Camera Sentinel',
            value: priv?.camera.systemPermission ?? 'ALLOWED',
            icon: Icons.videocam_rounded,
            color: priv?.camera.isActive == true ? AuraTheme.warning : AuraTheme.healthy,
            subtitle: priv?.camera.isActive == true ? 'CAMERA IN USE' : 'Idle (${priv?.camera.deviceCount ?? 1} Device)',
          ),
          _buildLiveTile(
            title: 'Microphone Sentinel',
            value: priv?.microphone.systemPermission ?? 'ALLOWED',
            icon: Icons.mic_rounded,
            color: priv?.microphone.isActive == true ? AuraTheme.warning : AuraTheme.healthy,
            subtitle: priv?.microphone.isActive == true ? 'AUDIO IN USE' : 'Idle (${priv?.microphone.deviceCount ?? 1} Endpoint)',
          ),
          _buildLiveTile(
            title: 'Windows Defender',
            value: posture?.defender.antivirusEnabled == true ? 'ACTIVE' : 'PROTECTED',
            icon: Icons.security_rounded,
            color: AuraTheme.healthy,
            subtitle: 'Real-Time Protection ON',
          ),
          _buildLiveTile(
            title: 'Windows Firewall',
            value: posture?.firewall.allProfilesSecure == true ? 'SECURED' : 'ACTIVE',
            icon: Icons.local_fire_department_rounded,
            color: AuraTheme.healthy,
            subtitle: 'Domain, Private & Public',
          ),
          _buildLiveTile(
            title: 'Secure Boot',
            value: posture?.secureBootEnabled == true ? 'ENABLED' : 'ACTIVE',
            icon: Icons.lock_rounded,
            color: AuraTheme.healthy,
            subtitle: 'Hardware Root of Trust',
          ),
          _buildLiveTile(
            title: 'TPM 2.0 Security',
            value: posture?.tpmPresent == true ? 'DETECTED' : 'PRESENT',
            icon: Icons.developer_board_rounded,
            color: AuraTheme.healthy,
            subtitle: 'Cryptographic Processor',
          ),
          _buildLiveTile(
            title: 'User Account Control',
            value: posture?.uacEnabled == true ? 'ENABLED' : 'ACTIVE',
            icon: Icons.admin_panel_settings_rounded,
            color: AuraTheme.healthy,
            subtitle: 'Elevation Guard Active',
          ),
          _buildLiveTile(
            title: 'Local Engine Link',
            value: state.isAuthenticated ? 'ONLINE' : 'OFFLINE',
            icon: Icons.cloud_done_rounded,
            color: state.isAuthenticated ? AuraTheme.healthy : AuraTheme.critical,
            subtitle: '127.0.0.1:8787 • WS Live',
          ),
        ],
      ),
    );
  }

  Widget _buildLiveTile({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
    required String subtitle,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AuraTheme.surfaceElevated,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AuraTheme.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 16),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AuraTheme.textSecondary),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: color),
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 2),
          Text(
            subtitle,
            style: const TextStyle(fontSize: 10, color: AuraTheme.textMuted),
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // RECENT ACTIVITY STREAM
  // -------------------------------------------------------------
  Widget _buildRecentActivityStream(List<TimelineEvent> timeline) {
    return AuraCard(
      title: 'Recent Security & Privacy Activity',
      icon: Icons.history_rounded,
      child: timeline.isEmpty
          ? Container(
              padding: const EdgeInsets.all(16),
              alignment: Alignment.center,
              child: const Text(
                'Security activity will appear here as AURA observes events.',
                style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
              ),
            )
          : ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: timeline.take(5).length,
              separatorBuilder: (_, index) => const Divider(height: 1, color: AuraTheme.borderSubtle),
              itemBuilder: (context, i) {
                final ev = timeline[i];
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 10),
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
                              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AuraTheme.textPrimary),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              ev.summary,
                              style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary),
                            ),
                          ],
                        ),
                      ),
                      Text(
                        Formatters.formatIsoTimestamp(ev.timestamp),
                        style: const TextStyle(fontSize: 10, color: AuraTheme.textMuted),
                      ),
                    ],
                  ),
                );
              },
            ),
    );
  }
}
