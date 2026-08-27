import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../models/scan.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/metric_gauge.dart';
import '../widgets/severity_badge.dart';
import '../widgets/aura_evidence_graph.dart';
import '../widgets/aura_status_badge.dart';

class ScanView extends StatefulWidget {
  const ScanView({super.key});

  @override
  State<ScanView> createState() => _ScanViewState();
}

class _ScanViewState extends State<ScanView> {
  String _selectedSeverityFilter = 'ALL';
  String? _expandedFindingId;

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final scan = state.latestScan;

    // Check if a target finding was specified via cross-navigation
    if (state.targetFindingId != null && _expandedFindingId == null) {
      _expandedFindingId = state.targetFindingId;
    }

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

            // Executive Narrative & Most Important Observation
            _buildExecutiveNarrativeCard(scan, state),
            const SizedBox(height: 24),

            // Findings Explorer
            _buildFindingsSection(scan, state),
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
      title: 'AURA Full Security Assessment',
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
          state.isScanning ? 'ASSESSING YOUR PC...' : 'RUN FULL ASSESSMENT',
          style: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.8),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'AURA correlates Windows security posture, hardware privacy sentinels, process DNA, network exposure, persistence mechanisms, and behavioural AI anomalies across this PC.',
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
                    const Icon(Icons.sync_rounded, size: 14, color: AuraTheme.primaryLight),
                    const SizedBox(width: 6),
                    Text(
                      'Phase: ${state.scanCurrentCategory}',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.primaryLight),
                    ),
                  ],
                ),
                Text(
                  '${(state.scanProgress * 100).toInt()}% completed',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary),
                ),
              ],
            ),
          ] else if (scan != null) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                const Icon(Icons.check_circle_rounded, size: 14, color: AuraTheme.healthy),
                const SizedBox(width: 6),
                Text(
                  'Assessment completed at ${scan.timestamp.toLocal().toString().substring(0, 19)}. Audited 9 security dimensions.',
                  style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // SCAN OVERVIEW GAUGES (POSTURE ROLLUP)
  // -------------------------------------------------------------
  Widget _buildScanOverviewSection(FullScanReport scan) {
    return AuraCard(
      title: 'Current Posture Rollup & Risk Envelope',
      icon: Icons.speed_rounded,
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: ScoreMetricGauge(
                  score: 100 - scan.compositeRiskScore,
                  label: 'System Posture',
                  subtitle: scan.compositeRiskScore < 30 ? 'Nominal Baseline' : 'Requires Review',
                  color: scan.compositeRiskScore < 30 ? AuraTheme.healthy : AuraTheme.warning,
                ),
              ),
              Expanded(
                child: ScoreMetricGauge(
                  score: scan.securityScore,
                  label: 'Protection Matrix',
                  subtitle: '${scan.hardwareSecurityState.tpmPresent ? "TPM 2.0" : "Std"} | Defender Active',
                  color: scan.securityScore >= 80 ? AuraTheme.healthy : AuraTheme.warning,
                ),
              ),
              Expanded(
                child: ScoreMetricGauge(
                  score: scan.privacyScore,
                  label: 'Privacy Sentinel',
                  subtitle: 'Zero Media Captured',
                  color: scan.privacyScore >= 80 ? AuraTheme.healthy : AuraTheme.warning,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          const Divider(height: 1, color: AuraTheme.borderSubtle),
          const SizedBox(height: 12),

          // Severity Summary Counters
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildSeverityCounter('CRITICAL', scan.criticalCount, AuraTheme.critical),
              _buildSeverityCounter('HIGH', scan.highCount, AuraTheme.high),
              _buildSeverityCounter('MEDIUM', scan.mediumCount, AuraTheme.warning),
              _buildSeverityCounter('LOW', scan.lowCount, AuraTheme.primaryLight),
              _buildSeverityCounter('INFO', scan.infoCount, AuraTheme.healthy),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSeverityCounter(String label, int count, Color color) {
    return Column(
      children: [
        Text(
          '$count',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: count > 0 ? color : AuraTheme.textSecondary),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary, letterSpacing: 0.6),
        ),
      ],
    );
  }

  // -------------------------------------------------------------
  // EXECUTIVE NARRATIVE & OBSERVATION
  // -------------------------------------------------------------
  Widget _buildExecutiveNarrativeCard(FullScanReport scan, AuraStateProvider state) {
    return AuraCard(
      title: 'Executive Assessment Narrative',
      icon: Icons.notes_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AuraTheme.surfaceElevated,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AuraTheme.borderSubtle),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.format_quote_rounded, color: AuraTheme.primaryLight, size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    scan.executiveSummary,
                    style: const TextStyle(fontSize: 13, height: 1.4, color: AuraTheme.textPrimary, fontWeight: FontWeight.w500),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              const Icon(Icons.psychology_outlined, size: 16, color: AuraTheme.primaryLight),
              const SizedBox(width: 8),
              const Text('Most Important Observation: ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
              Expanded(
                child: Text(
                  scan.findings.isNotEmpty ? scan.findings.first.title : 'System baseline is stable and operating within nominal parameters.',
                  style: const TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // FINDINGS EXPLORER WITH EVIDENCE GRAPH
  // -------------------------------------------------------------
  Widget _buildFindingsSection(FullScanReport scan, AuraStateProvider state) {
    var list = scan.findings;
    if (_selectedSeverityFilter != 'ALL') {
      list = list.where((f) => f.severity.toUpperCase() == _selectedSeverityFilter).toList();
    }

    return AuraCard(
      title: 'Security Findings & Correlated Evidence (${list.length})',
      icon: Icons.search_rounded,
      trailing: Wrap(
        spacing: 6,
        children: ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'].map((sev) {
          final isSel = _selectedSeverityFilter == sev;
          return ChoiceChip(
            label: Text(sev, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: isSel ? Colors.black : AuraTheme.textSecondary)),
            selected: isSel,
            selectedColor: AuraTheme.primaryLight,
            backgroundColor: AuraTheme.surfaceElevated,
            onSelected: (_) => setState(() => _selectedSeverityFilter = sev),
          );
        }).toList(),
      ),
      child: list.isEmpty
          ? const Padding(
              padding: EdgeInsets.symmetric(vertical: 24),
              child: Center(
                child: Text(
                  'No findings matched the selected severity filter.',
                  style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
                ),
              ),
            )
          : ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: list.length,
              separatorBuilder: (_, index) => const SizedBox(height: 12),
              itemBuilder: (context, i) {
                final finding = list[i];
                final isExpanded = _expandedFindingId == finding.id;

                return Container(
                  decoration: BoxDecoration(
                    color: AuraTheme.surfaceElevated,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: isExpanded ? AuraTheme.primaryLight.withValues(alpha: 0.6) : AuraTheme.borderSubtle,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Header clickable bar
                      InkWell(
                        onTap: () {
                          setState(() {
                            _expandedFindingId = isExpanded ? null : finding.id;
                          });
                        },
                        borderRadius: BorderRadius.circular(10),
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: Row(
                            children: [
                              SeverityBadge(severity: finding.severity),
                              const SizedBox(width: 10),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: AuraTheme.surface,
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(color: AuraTheme.borderSubtle),
                                ),
                                child: Text(
                                  finding.category,
                                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  finding.title,
                                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                                ),
                              ),
                              const SizedBox(width: 8),
                              AuraStatusBadge(status: finding.observationState, fontSize: 10),
                              const SizedBox(width: 8),
                              Icon(
                                isExpanded ? Icons.expand_less_rounded : Icons.expand_more_rounded,
                                color: AuraTheme.textSecondary,
                                size: 18,
                              ),
                            ],
                          ),
                        ),
                      ),

                      // Expanded Details & Evidence Graph
                      if (isExpanded) ...[
                        const Divider(height: 1, color: AuraTheme.borderSubtle),
                        Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // 1. What Happened & Why it Matters
                              const Text('WHAT AURA OBSERVED:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AuraTheme.primaryLight)),
                              const SizedBox(height: 4),
                              Text(finding.description, style: const TextStyle(fontSize: 12, height: 1.4, color: AuraTheme.textPrimary)),
                              const SizedBox(height: 12),

                              if (finding.remediation.isNotEmpty) ...[
                                const Text('RECOMMENDED ACTION:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AuraTheme.healthy)),
                                const SizedBox(height: 4),
                                Text(finding.remediation, style: const TextStyle(fontSize: 12, height: 1.4, color: AuraTheme.textSecondary)),
                                const SizedBox(height: 16),
                              ],

                              // 2. Interactive Cross-Signal Evidence Graph
                              AuraEvidenceGraph(
                                processName: finding.associatedProcess ?? 'Host System Activity',
                                pid: finding.pid,
                                networkTarget: finding.associatedIp,
                                persistenceType: finding.category == 'PERSISTENCE' ? 'Registry / Service' : null,
                                anomalyReason: 'Multi-Signal Correlation',
                                privacyTarget: finding.category == 'PRIVACY' ? 'Camera / Mic' : null,
                                findingTitle: finding.title,
                                severity: finding.severity,
                                onProcessClick: (pid) => state.navigateTo(4, targetPid: pid),
                                onNetworkClick: (ip) => state.navigateTo(5, targetIp: ip),
                                onPersistenceClick: () => state.navigateTo(6),
                                onPrivacyClick: () => state.navigateTo(3),
                              ),
                              const SizedBox(height: 16),

                              // 3. What AURA Knows vs What AURA Does Not Know
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    child: Container(
                                      padding: const EdgeInsets.all(12),
                                      decoration: BoxDecoration(
                                        color: AuraTheme.surface,
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(color: AuraTheme.healthy.withValues(alpha: 0.3)),
                                      ),
                                      child: const Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Icon(Icons.check_circle_outline_rounded, size: 14, color: AuraTheme.healthy),
                                              SizedBox(width: 6),
                                              Text('WHAT AURA KNOWS (OBSERVED)', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: AuraTheme.healthy)),
                                            ],
                                          ),
                                          SizedBox(height: 6),
                                          Text('• Process binary metadata & elevation state\n• Network endpoint classification\n• Windows security posture state', style: TextStyle(fontSize: 11, color: AuraTheme.textSecondary, height: 1.3)),
                                        ],
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Container(
                                      padding: const EdgeInsets.all(12),
                                      decoration: BoxDecoration(
                                        color: AuraTheme.surface,
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(color: AuraTheme.primaryLight.withValues(alpha: 0.3)),
                                      ),
                                      child: const Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Icon(Icons.shield_outlined, size: 14, color: AuraTheme.primaryLight),
                                              SizedBox(width: 6),
                                              Text('WHAT AURA DOES NOT TOUCH', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: AuraTheme.primaryLight)),
                                            ],
                                          ),
                                          SizedBox(height: 6),
                                          Text('• Zero media / video recording\n• Zero audio capture or voice storage\n• Zero packet payload inspection', style: TextStyle(fontSize: 11, color: AuraTheme.textSecondary, height: 1.3)),
                                        ],
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 16),

                              // Quick Action CTAs
                              Row(
                                children: [
                                  if (finding.pid != null) ...[
                                    ElevatedButton.icon(
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: AuraTheme.primary,
                                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                      ),
                                      onPressed: () => state.navigateTo(4, targetPid: finding.pid),
                                      icon: const Icon(Icons.memory_rounded, size: 14, color: Colors.white),
                                      label: Text('INSPECT PID ${finding.pid} DNA', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Colors.white)),
                                    ),
                                    const SizedBox(width: 10),
                                  ],
                                  if (finding.associatedIp != null) ...[
                                    OutlinedButton.icon(
                                      style: OutlinedButton.styleFrom(
                                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                        side: const BorderSide(color: AuraTheme.border),
                                      ),
                                      onPressed: () => state.navigateTo(5, targetIp: finding.associatedIp),
                                      icon: const Icon(Icons.language_rounded, size: 14),
                                      label: Text('TRACE ${finding.associatedIp}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                                    ),
                                    const SizedBox(width: 10),
                                  ],
                                  OutlinedButton.icon(
                                    style: OutlinedButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                      side: const BorderSide(color: AuraTheme.border),
                                    ),
                                    onPressed: () => state.navigateTo(8),
                                    icon: const Icon(Icons.assignment_outlined, size: 14),
                                    label: const Text('CREATE INCIDENT CASE', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                );
              },
            ),
    );
  }

  // -------------------------------------------------------------
  // PRE-SCAN 9 CATEGORIES GRID
  // -------------------------------------------------------------
  Widget _buildPreScanCategoriesGrid() {
    final categories = [
      _CategoryInfo('Hardware Security Architecture', 'TPM 2.0, Secure Boot state, and physical device boundaries.', Icons.lock_outline_rounded),
      _CategoryInfo('Kernel & Subsystem Protections', 'Memory integrity, hypervisor-enforced code integrity, and UAC.', Icons.memory_rounded),
      _CategoryInfo('Antivirus Real-Time Defense', 'Windows Defender real-time engine and signature freshness.', Icons.security_rounded),
      _CategoryInfo('Windows Defender Firewall', 'Domain, Private, and Public network firewall active profiles.', Icons.shield_outlined),
      _CategoryInfo('Authentication & Credential Isolation', 'LSA protection, credential guard, and elevation policies.', Icons.key_rounded),
      _CategoryInfo('Hardware Privacy Sentinels', 'Windows webcam registry flags and audio stream activity monitors.', Icons.videocam_rounded),
      _CategoryInfo('Process Execution DNA', 'Active process trees, CPU/memory outliers, and binary SHA-256 digests.', Icons.account_tree_rounded),
      _CategoryInfo('Network Exposure Matrix', 'Active socket flows, listening ports, and public IP classifications.', Icons.hub_rounded),
      _CategoryInfo('Persistence Mechanisms', 'Auto-start registry keys, Windows services, and scheduled tasks.', Icons.push_pin_rounded),
    ];

    return AuraCard(
      title: '9 Security Assessment Checkpoints',
      icon: Icons.checklist_rounded,
      child: GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 3,
          childAspectRatio: 2.3,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
        ),
        itemCount: categories.length,
        itemBuilder: (context, i) {
          final cat = categories[i];
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
                    Icon(cat.icon, size: 16, color: AuraTheme.primaryLight),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        cat.title,
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  cat.desc,
                  style: const TextStyle(fontSize: 10, color: AuraTheme.textSecondary, height: 1.3),
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
  // HONEST SECURITY BOUNDARY CARD
  // -------------------------------------------------------------
  Widget _buildHonestBoundaryCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AuraTheme.surfaceElevated,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AuraTheme.borderSubtle),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.privacy_tip_outlined, color: AuraTheme.healthy, size: 22),
          SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'AURA HONEST ASSESSMENT BOUNDARY',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.0,
                    color: AuraTheme.healthy,
                  ),
                ),
                SizedBox(height: 4),
                Text(
                  'AURA assesses security configuration, telemetry deviations, and privacy access metadata. It does not claim full-disk malware scanning or kernel-level packet inspection. All evaluations run locally on your Windows PC.',
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

class _CategoryInfo {
  final String title;
  final String desc;
  final IconData icon;

  _CategoryInfo(this.title, this.desc, this.icon);
}
