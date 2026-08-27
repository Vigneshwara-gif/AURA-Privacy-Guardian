import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../models/network_intel.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';

class NetworkIntelView extends StatefulWidget {
  const NetworkIntelView({super.key});

  @override
  State<NetworkIntelView> createState() => _NetworkIntelViewState();
}

class _NetworkIntelViewState extends State<NetworkIntelView> {
  String _flowFilter = 'ALL'; // ALL, ESTABLISHED, LISTENING, PUBLIC

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final net = state.network;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Topology & Attack Surface Metric Tiles
          _buildTopologyOverviewCard(net),
          const SizedBox(height: 24),

          // 2. Inbound Exposure Checkpoints
          _buildExposureCheckpointsCard(net),
          const SizedBox(height: 24),

          // 3. Observed Socket Flows & Remote Endpoints
          _buildSocketFlowsCard(net, state),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // TOPOLOGY OVERVIEW
  // -------------------------------------------------------------
  Widget _buildTopologyOverviewCard(NetworkInvestigation? net) {
    return AuraCard(
      title: 'Socket Flow Investigation & Attack Surface Topology',
      icon: Icons.hub_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Understand what your PC is communicating with in real time. AURA monitors active socket descriptors and classifies endpoints without capturing or inspecting packet contents.',
            style: TextStyle(fontSize: 13, color: AuraTheme.textSecondary, height: 1.4),
          ),
          const SizedBox(height: 16),

          Row(
            children: [
              _buildNetStatTile('Active Sockets', '${net?.totalConnections ?? 0}', 'Total open descriptors'),
              const SizedBox(width: 12),
              _buildNetStatTile('Established Flows', '${net?.establishedCount ?? 0}', 'Active two-way connections'),
              const SizedBox(width: 12),
              _buildNetStatTile('Listening Ports', '${net?.listeningCount ?? 0}', 'Inbound listening endpoints'),
              const SizedBox(width: 12),
              _buildNetStatTile('Public Internet Egress', '${net?.remotePublicCount ?? 0}', 'Outbound WAN connections', isAlert: (net?.remotePublicCount ?? 0) > 10),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildNetStatTile(String title, String value, String subtitle, {bool isAlert = false}) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AuraTheme.surfaceElevated,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: isAlert ? AuraTheme.warning.withValues(alpha: 0.4) : AuraTheme.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AuraTheme.textSecondary)),
            const SizedBox(height: 6),
            Text(value, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: isAlert ? AuraTheme.warning : AuraTheme.textPrimary)),
            const SizedBox(height: 2),
            Text(subtitle, style: const TextStyle(fontSize: 10, color: AuraTheme.textMuted)),
          ],
        ),
      ),
    );
  }

  // -------------------------------------------------------------
  // INBOUND EXPOSURE CHECKPOINTS
  // -------------------------------------------------------------
  Widget _buildExposureCheckpointsCard(NetworkInvestigation? net) {
    final findings = net?.exposureFindings ?? [];

    return AuraCard(
      title: 'Inbound Exposure & Listening Checkpoints (${findings.length})',
      icon: Icons.warning_amber_rounded,
      child: findings.isEmpty
          ? Container(
              padding: const EdgeInsets.all(20),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: AuraTheme.healthy.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AuraTheme.healthy.withValues(alpha: 0.25)),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.check_circle_rounded, color: AuraTheme.healthy, size: 20),
                  SizedBox(width: 10),
                  Text('Zero unprotected listening ports discovered. Windows Firewall posture is active.', style: TextStyle(color: AuraTheme.healthy)),
                ],
              ),
            )
          : Column(
              children: findings.map((f) {
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
                      SeverityBadge(severity: f.severity),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(f.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
                            const SizedBox(height: 2),
                            Text('Recommendation: ${f.recommendation}', style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: AuraTheme.primary.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'Port ${f.port}/${f.protocol}',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: AuraTheme.primaryLight),
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
    );
  }

  // -------------------------------------------------------------
  // SOCKET FLOWS & OBSERVED ENDPOINTS
  // -------------------------------------------------------------
  Widget _buildSocketFlowsCard(NetworkInvestigation? net, AuraStateProvider state) {
    final endpoints = net?.activeEndpoints ?? [];

    final filtered = endpoints.where((e) {
      if (_flowFilter == 'ALL') return true;
      if (_flowFilter == 'PUBLIC') return e.classification.toUpperCase() == 'PUBLIC';
      if (_flowFilter == 'ESTABLISHED') return e.state.toUpperCase() == 'ESTABLISHED';
      if (_flowFilter == 'LISTENING') return e.state.toUpperCase() == 'LISTEN' || e.state.toUpperCase() == 'LISTENING';
      return true;
    }).toList();

    return AuraCard(
      title: 'Observed Socket Flows & Endpoints (${filtered.length})',
      icon: Icons.public_rounded,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildFilterChip('ALL', 'All'),
          _buildFilterChip('PUBLIC', 'Public WAN'),
          _buildFilterChip('ESTABLISHED', 'Established'),
          _buildFilterChip('LISTENING', 'Listening'),
        ],
      ),
      child: filtered.isEmpty
          ? Container(
              padding: const EdgeInsets.all(24),
              alignment: Alignment.center,
              child: const Text('No network socket endpoints match this filter.', style: TextStyle(color: AuraTheme.textSecondary)),
            )
          : ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: filtered.take(20).length,
              separatorBuilder: (_, index) => const Divider(height: 1, color: AuraTheme.borderSubtle),
              itemBuilder: (context, i) {
                final e = filtered[i];
                final isPublic = e.classification.toUpperCase() == 'PUBLIC';

                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: AuraTheme.surfaceElevated,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Icon(
                          isPublic ? Icons.public_rounded : Icons.lan_rounded,
                          size: 16,
                          color: isPublic ? AuraTheme.warning : AuraTheme.primaryLight,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        flex: 3,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${e.ip}:${e.port}',
                              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: AuraTheme.textPrimary),
                            ),
                            InkWell(
                              onTap: e.pid != null ? () => state.navigateTo(4, targetPid: e.pid) : null,
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    '${e.processName ?? "System"} (PID ${e.pid ?? 0})',
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: e.pid != null ? AuraTheme.primaryLight : AuraTheme.textSecondary,
                                      fontWeight: e.pid != null ? FontWeight.w700 : FontWeight.w500,
                                      decoration: e.pid != null ? TextDecoration.underline : TextDecoration.none,
                                    ),
                                  ),
                                  Text(
                                    ' • ${e.protocol}',
                                    style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      Expanded(
                        flex: 2,
                        child: Text(
                          e.state,
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AuraTheme.textSecondary),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: (isPublic ? AuraTheme.warning : AuraTheme.healthy).withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          e.classification,
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            color: isPublic ? AuraTheme.warning : AuraTheme.healthy,
                          ),
                        ),
                      ),
                      if (e.pid != null) ...[
                        const SizedBox(width: 8),
                        IconButton(
                          icon: const Icon(Icons.arrow_forward_rounded, size: 14, color: AuraTheme.primaryLight),
                          tooltip: 'Inspect Process DNA for PID ${e.pid}',
                          onPressed: () => state.navigateTo(4, targetPid: e.pid),
                        ),
                      ],
                    ],
                  ),
                );
              },
            ),
    );
  }

  Widget _buildFilterChip(String key, String label) {
    final isSelected = _flowFilter == key;
    return Padding(
      padding: const EdgeInsets.only(left: 6),
      child: InkWell(
        onTap: () => setState(() => _flowFilter = key),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
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
}
