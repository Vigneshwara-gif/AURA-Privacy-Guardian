import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';

class NetworkIntelView extends StatelessWidget {
  const NetworkIntelView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final net = state.network;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Topology Overview
          AuraCard(
            title: 'Socket Flow Investigation & Attack Surface Topology',
            icon: Icons.hub_rounded,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _NetStat(title: 'Active Sockets', value: '${net?.totalConnections ?? 0}'),
                    const SizedBox(width: 12),
                    _NetStat(title: 'Established Flows', value: '${net?.establishedCount ?? 0}'),
                    const SizedBox(width: 12),
                    _NetStat(title: 'Listening Endpoints', value: '${net?.listeningCount ?? 0}'),
                    const SizedBox(width: 12),
                    _NetStat(title: 'Public Internet Egress', value: '${net?.remotePublicCount ?? 0}'),
                  ],
                ),
                const SizedBox(height: 16),
                Text(net?.summary ?? 'Analyzing active network socket descriptors...',
                    style: const TextStyle(fontSize: 12, color: AuraTheme.textSecondary)),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Inbound Port Exposure Checkpoints
          AuraCard(
            title: 'Inbound Exposure Checkpoints (${net?.exposureFindings.length ?? 0})',
            icon: Icons.warning_amber_rounded,
            child: (net?.exposureFindings.isEmpty ?? true)
                ? const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16),
                    child: Center(
                      child: Text('Zero unprotected listening ports discovered. Firewall posture is active.',
                          style: TextStyle(color: AuraTheme.healthy)),
                    ),
                  )
                : Column(
                    children: net!.exposureFindings.map((f) {
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
                                  Text(f.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
                                  Text('Recommendation: ${f.recommendation}', style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
                                ],
                              ),
                            ),
                            Text('Port ${f.port}/${f.protocol}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.primaryLight)),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
          ),
          const SizedBox(height: 24),

          // Active Socket Endpoints
          AuraCard(
            title: 'Observed Remote Network Endpoints',
            icon: Icons.public_rounded,
            child: (net?.activeEndpoints.isEmpty ?? true)
                ? const Text('No remote IP endpoints active.')
                : Column(
                    children: net!.activeEndpoints.take(15).map((e) {
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: Row(
                          children: [
                            Icon(Icons.router_rounded, size: 14, color: e.classification == 'PUBLIC_INTERNET' ? AuraTheme.medium : AuraTheme.primaryLight),
                            const SizedBox(width: 10),
                            SizedBox(
                              width: 160,
                              child: Text('${e.ip}:${e.port}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(color: AuraTheme.surfaceElevated, borderRadius: BorderRadius.circular(4)),
                              child: Text(e.classification, style: const TextStyle(fontSize: 10, color: AuraTheme.textSecondary)),
                            ),
                            const Spacer(),
                            Text('${e.processName ?? "Unknown"} (PID ${e.pid ?? "N/A"})', style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
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

class _NetStat extends StatelessWidget {
  final String title;
  final String value;
  const _NetStat({required this.title, required this.value});

  @override
  Widget build(BuildContext context) {
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
            Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AuraTheme.textPrimary)),
          ],
        ),
      ),
    );
  }
}
