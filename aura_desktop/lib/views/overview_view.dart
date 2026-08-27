import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../core/utils/formatters.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';
import '../widgets/aura_status_badge.dart';

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
    final story = state.liveSystemStory;

    final secScore = posture?.overallPostureScore ?? 100;
    final privScore = priv?.overallPrivacyScore ?? 100;
    final compRisk = scan?.compositeRiskScore ?? (secScore < 80 ? 35 : 15);

    // Determine primary status and human rationale
    String statusTitle;
    String statusWhy;
    Color statusColor;
    IconData statusIcon;

    if (!state.isAuthenticated) {
      statusTitle = 'AGENT DISCONNECTED';
      statusWhy = 'Local security engine is offline or reconnecting over loopback (127.0.0.1:8787).';
      statusColor = AuraTheme.critical;
      statusIcon = Icons.link_off_rounded;
    } else if (state.isScanning) {
      statusTitle = 'SECURITY AUDIT IN PROGRESS';
      statusWhy = 'Evaluating 9 PC security dimensions (${state.scanCurrentCategory})...';
      statusColor = AuraTheme.primaryLight;
      statusIcon = Icons.radar_rounded;
    } else if (compRisk >= 60 || findings.any((f) => f.severity == 'CRITICAL' || f.severity == 'HIGH')) {
      statusTitle = 'INVESTIGATION REQUIRED';
      statusWhy = 'AURA identified high-severity configuration risks or active deviations requiring investigation.';
      statusColor = AuraTheme.critical;
      statusIcon = Icons.warning_amber_rounded;
    } else if (findings.isNotEmpty) {
      statusTitle = 'ATTENTION REQUIRED';
      final topF = findings.first;
      statusWhy = 'Your PC is protected, with ${findings.length == 1 ? "1 item" : "${findings.length} items"} worth reviewing: ${topF.title}. No confirmed compromise detected.';
      statusColor = AuraTheme.warning;
      statusIcon = Icons.info_outline_rounded;
    } else {
      statusTitle = 'PROTECTED';
      statusWhy = 'Core Windows security controls are active and no unauthorized hardware or network behaviors are observed.';
      statusColor = AuraTheme.healthy;
      statusIcon = Icons.verified_user_rounded;
    }

    final hasAnomaly = state.aiExplanation?.isAnomaly == true || findings.any((f) => f.category == 'AI_ANOMALY');
    final riskyExposures = state.network?.exposureFindings.where((f) => f.severity == 'HIGH' || f.severity == 'CRITICAL').length ?? 0;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Primary Hero Status Banner with "WHY?"
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
                              fontSize: 12,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 1.2,
                              color: AuraTheme.textSecondary,
                            ),
                          ),
                          Text(
                            statusTitle,
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 1.2,
                              color: statusColor,
                            ),
                          ),
                          const SizedBox(width: 12),
                          AuraStatusBadge(status: statusTitle, fontSize: 10),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        statusWhy,
                        style: const TextStyle(
                          fontSize: 13,
                          color: AuraTheme.textPrimary,
                          fontWeight: FontWeight.w500,
                          height: 1.4,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        state.machineReadinessSummary,
                        style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 20),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: statusColor == AuraTheme.healthy ? AuraTheme.primary : statusColor,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onPressed: state.isScanning ? null : () => state.runFullSecurityScan(),
                  icon: state.isScanning
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.radar_rounded, size: 18),
                  label: Text(
                    state.isScanning ? 'ASSESSING...' : 'RUN FULL AUDIT',
                    style: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.8),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // 2. Coherent Posture Composition: 4 Core Quadrants
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Quadrant 1: PROTECTION
              Expanded(
                child: _buildPostureQuadrant(
                  icon: Icons.shield_outlined,
                  title: 'PROTECTION',
                  scoreLabel: '$secScore/100',
                  statusText: posture?.antivirus.realtimeProtection == true ? 'Antivirus Real-Time Active' : 'Check Windows Defender',
                  isHealthy: posture?.antivirus.realtimeProtection == true,
                  subItems: [
                    'Defender: ${posture?.antivirus.name ?? "Active"}',
                    'Firewall: ${posture?.firewall.domainProfile == true ? "Protected" : "Standard"}',
                    'TPM: ${posture?.hardwareSecurity.tpmPresent == true ? "TPM 2.0 Present" : "Standard"}',
                  ],
                  onTap: () => state.navigateTo(1),
                ),
              ),
              const SizedBox(width: 16),

              // Quadrant 2: PRIVACY
              Expanded(
                child: _buildPostureQuadrant(
                  icon: Icons.lock_outline_rounded,
                  title: 'PRIVACY',
                  scoreLabel: '$privScore/100',
                  statusText: priv?.camera.isActive == true ? 'Camera Sensor Active' : 'Zero Media Captured',
                  isHealthy: priv?.camera.isActive != true,
                  subItems: [
                    'Camera: ${priv?.camera.summaryState ?? "Ready & Idle"}',
                    'Microphone: ${priv?.microphone.summaryState ?? "Ready & Idle"}',
                    'Zero-Media Policy Enforced',
                  ],
                  onTap: () => state.navigateTo(3),
                ),
              ),
              const SizedBox(width: 16),

              // Quadrant 3: BEHAVIOUR
              Expanded(
                child: _buildPostureQuadrant(
                  icon: Icons.psychology_outlined,
                  title: 'BEHAVIOUR',
                  scoreLabel: hasAnomaly ? 'REVIEW' : 'NOMINAL',
                  statusText: hasAnomaly ? 'Statistical Deviation Observed' : 'Nominal Behavioral Baseline',
                  isHealthy: !hasAnomaly,
                  subItems: [
                    'Baseline: 10-D Welford Tracking',
                    'Current: ${hasAnomaly ? (state.aiExplanation?.primarySignal ?? "Deviation Noted") : "Nominal Envelope"}',
                    'AI Model: Isolation Forest + LOF',
                  ],
                  onTap: () => state.navigateTo(2),
                ),
              ),
              const SizedBox(width: 16),

              // Quadrant 4: EXPOSURE
              Expanded(
                child: _buildPostureQuadrant(
                  icon: Icons.hub_outlined,
                  title: 'EXPOSURE',
                  scoreLabel: riskyExposures > 0 ? 'ELEVATED' : ((state.network?.publicIpCount ?? 0) > 20 ? 'MODERATE' : 'LOW'),
                  statusText: '${state.network?.activeConnectionsCount ?? 0} Sockets Observed',
                  isHealthy: riskyExposures == 0,
                  subItems: [
                    'Public WAN: ${state.network?.publicIpCount ?? 0} Destinations',
                    'Listeners: ${state.network?.listeningPortsCount ?? 0} Endpoints',
                    'High-Risk: $riskyExposures Confirmed',
                  ],
                  onTap: () => state.navigateTo(5),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // 3. Middle Section: Next Best Action & Live System Watch
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Left: Next Best Action Card
              Expanded(
                flex: 4,
                child: AuraCard(
                  title: 'Next Recommended Action',
                  icon: Icons.lightbulb_outline_rounded,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (findings.isNotEmpty) ...[
                        Row(
                          children: [
                            SeverityBadge(severity: findings.first.severity),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                findings.first.title,
                                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          findings.first.description,
                          style: const TextStyle(fontSize: 12, color: AuraTheme.textSecondary, height: 1.4),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 16),
                        Row(
                          children: [
                            ElevatedButton.icon(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AuraTheme.primary,
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                              ),
                              onPressed: () => state.navigateTo(1, targetFindingId: findings.first.id),
                              icon: const Icon(Icons.search_rounded, size: 14, color: Colors.white),
                              label: const Text('INVESTIGATE FINDING', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Colors.white)),
                            ),
                            const SizedBox(width: 10),
                            OutlinedButton(
                              style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                                side: const BorderSide(color: AuraTheme.border),
                              ),
                              onPressed: () => state.navigateTo(1),
                              child: const Text('VIEW ALL FINDINGS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
                            ),
                          ],
                        ),
                      ] else ...[
                        const Row(
                          children: [
                            Icon(Icons.check_circle_outline_rounded, color: AuraTheme.healthy, size: 20),
                            SizedBox(width: 10),
                            Text(
                              'Security Baseline is Nominal',
                              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'No immediate security risks or unexpected hardware activations require intervention. AURA continues real-time loopback monitoring.',
                          style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary, height: 1.4),
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AuraTheme.surfaceElevated,
                            side: const BorderSide(color: AuraTheme.border),
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                          ),
                          onPressed: () => state.navigateTo(1),
                          icon: const Icon(Icons.assignment_outlined, size: 14, color: AuraTheme.primaryLight),
                          label: const Text('VIEW AUDIT CHECKPOINTS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 16),

              // Right: Real-time Telemetry Pulse (What AURA is watching)
              Expanded(
                flex: 3,
                child: AuraCard(
                  title: 'Real-Time Execution Pulse',
                  icon: Icons.speed_rounded,
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: _buildMetricTile(
                              'Processes',
                              telem == null
                                  ? (state.isLoading ? 'LOADING...' : 'UNAVAILABLE')
                                  : (telem.processCount > 0 ? '${telem.processCount}' : '0'),
                              'Active Win32 Tree',
                              Icons.memory_rounded,
                              () => state.navigateTo(4),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: _buildMetricTile(
                              'CPU Load',
                              telem == null
                                  ? (state.isLoading ? 'LOADING...' : 'UNAVAILABLE')
                                  : '${telem.cpuPercent.toStringAsFixed(1)}%',
                              'Utilization',
                              Icons.insights_rounded,
                              null,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: _buildMetricTile(
                              'RAM Used',
                              telem == null
                                  ? (state.isLoading ? 'LOADING...' : 'UNAVAILABLE')
                                  : Formatters.formatBytes(telem.memoryUsedBytes),
                              'Physical RAM (${telem?.memoryPercent.toStringAsFixed(0) ?? 0}%)',
                              Icons.storage_rounded,
                              null,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: _buildMetricTile(
                              'Camera / Mic',
                              priv == null
                                  ? (state.isLoading ? 'LOADING...' : 'READY')
                                  : (priv.camera.isActive || priv.microphone.isActive ? 'Active Stream' : 'Idle & Monitored'),
                              'Zero-Media Enforced',
                              Icons.videocam_rounded,
                              () => state.navigateTo(3),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // 4. Live System Story (Real-time chronological feed)
          AuraCard(
            title: 'Live System Security Story',
            icon: Icons.history_edu_rounded,
            trailing: TextButton.icon(
              onPressed: () => state.navigateTo(9),
              icon: const Icon(Icons.arrow_forward_rounded, size: 14),
              label: const Text('FORENSIC TIMELINE', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            ),
            child: story.isEmpty
                ? const Padding(
                    padding: EdgeInsets.symmetric(vertical: 24),
                    child: Center(
                      child: Text(
                        'Listening for system telemetry events on local loopback...',
                        style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
                      ),
                    ),
                  )
                : ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: story.length > 6 ? 6 : story.length,
                    separatorBuilder: (_, index) => const Divider(height: 1, color: AuraTheme.borderSubtle),
                    itemBuilder: (context, i) {
                      final ev = story[i];
                      final sevColor = AuraTheme.getSeverityColor(ev.severity);

                      return ListTile(
                        dense: true,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                        leading: Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: sevColor.withValues(alpha: 0.12),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            _getCategoryIcon(ev.category),
                            color: sevColor,
                            size: 16,
                          ),
                        ),
                        title: Row(
                          children: [
                            Text(
                              Formatters.formatTimestamp(ev.timestamp),
                              style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: AuraTheme.textSecondary),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                              decoration: BoxDecoration(
                                color: AuraTheme.surfaceElevated,
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(color: AuraTheme.borderSubtle),
                              ),
                              child: Text(
                                ev.category,
                                style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: AuraTheme.primaryLight),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                ev.title,
                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                        subtitle: Padding(
                          padding: const EdgeInsets.only(top: 2),
                          child: Text(
                            ev.detail,
                            style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        trailing: ev.pid != null
                            ? OutlinedButton(
                                style: OutlinedButton.styleFrom(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  minimumSize: Size.zero,
                                  side: const BorderSide(color: AuraTheme.border),
                                ),
                                onPressed: () => state.navigateTo(4, targetPid: ev.pid),
                                child: Text('PID ${ev.pid}', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700)),
                              )
                            : null,
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildPostureQuadrant({
    required IconData icon,
    required String title,
    required String scoreLabel,
    required String statusText,
    required bool isHealthy,
    required List<String> subItems,
    required VoidCallback onTap,
  }) {
    final color = isHealthy ? AuraTheme.healthy : AuraTheme.warning;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AuraTheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AuraTheme.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 16, color: color),
                const SizedBox(width: 6),
                Text(
                  title,
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.0, color: AuraTheme.textPrimary),
                ),
                const Spacer(),
                Text(
                  scoreLabel,
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: color),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              statusText,
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: color),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),
            const Divider(height: 1, color: AuraTheme.borderSubtle),
            const SizedBox(height: 8),
            ...subItems.map(
              (item) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(
                  '• $item',
                  style: const TextStyle(fontSize: 10, color: AuraTheme.textSecondary),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricTile(String label, String value, String subtitle, IconData icon, VoidCallback? onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
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
                Text(
                  label,
                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              value,
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: AuraTheme.textPrimary),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: const TextStyle(fontSize: 9, color: AuraTheme.textSecondary),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getCategoryIcon(String cat) {
    switch (cat.toUpperCase()) {
      case 'PROCESS':
        return Icons.memory_rounded;
      case 'NETWORK':
        return Icons.language_rounded;
      case 'PRIVACY':
        return Icons.videocam_rounded;
      case 'BEHAVIOUR':
        return Icons.psychology_rounded;
      case 'FINDING':
        return Icons.security_rounded;
      default:
        return Icons.info_outline_rounded;
    }
  }
}
