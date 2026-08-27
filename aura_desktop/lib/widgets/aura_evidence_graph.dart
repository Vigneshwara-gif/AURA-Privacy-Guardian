import 'package:flutter/material.dart';
import '../core/theme/aura_theme.dart';

class AuraEvidenceGraph extends StatelessWidget {
  final String processName;
  final int? pid;
  final String? networkTarget;
  final String? persistenceType;
  final String? anomalyReason;
  final String? privacyTarget;
  final String findingTitle;
  final String severity;
  final Function(int pid)? onProcessClick;
  final Function(String ip)? onNetworkClick;
  final VoidCallback? onPersistenceClick;
  final VoidCallback? onPrivacyClick;

  const AuraEvidenceGraph({
    super.key,
    required this.processName,
    this.pid,
    this.networkTarget,
    this.persistenceType,
    this.anomalyReason,
    this.privacyTarget,
    required this.findingTitle,
    this.severity = 'MEDIUM',
    this.onProcessClick,
    this.onNetworkClick,
    this.onPersistenceClick,
    this.onPrivacyClick,
  });

  @override
  Widget build(BuildContext context) {
    final sevColor = AuraTheme.getSeverityColor(severity);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AuraTheme.surfaceElevated,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AuraTheme.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.hub_rounded, color: AuraTheme.primaryLight, size: 20),
              const SizedBox(width: 8),
              const Text(
                'CROSS-SIGNAL CORRELATION GRAPH',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.0,
                  color: AuraTheme.textPrimary,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AuraTheme.primaryLight.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text(
                  'INTERACTIVE DRILL-DOWN',
                  style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AuraTheme.primaryLight),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Flow of correlated nodes
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                // Node 1: Process
                _buildNode(
                  icon: Icons.memory_rounded,
                  category: 'PROCESS',
                  title: processName,
                  subtitle: pid != null ? 'PID $pid' : 'Execution',
                  color: AuraTheme.primaryLight,
                  onTap: pid != null && onProcessClick != null ? () => onProcessClick!(pid!) : null,
                ),
                _buildConnector(),

                // Node 2: Network (if present)
                if (networkTarget != null && networkTarget!.isNotEmpty) ...[
                  _buildNode(
                    icon: Icons.language_rounded,
                    category: 'NETWORK',
                    title: networkTarget!,
                    subtitle: 'Socket Flow',
                    color: Colors.cyanAccent,
                    onTap: onNetworkClick != null ? () => onNetworkClick!(networkTarget!) : null,
                  ),
                  _buildConnector(),
                ],

                // Node 3: Persistence (if present)
                if (persistenceType != null && persistenceType!.isNotEmpty) ...[
                  _buildNode(
                    icon: Icons.push_pin_rounded,
                    category: 'PERSISTENCE',
                    title: persistenceType!,
                    subtitle: 'Auto-Start',
                    color: Colors.purpleAccent,
                    onTap: onPersistenceClick,
                  ),
                  _buildConnector(),
                ],

                // Node 4: Privacy (if present)
                if (privacyTarget != null && privacyTarget!.isNotEmpty) ...[
                  _buildNode(
                    icon: Icons.videocam_rounded,
                    category: 'PRIVACY',
                    title: privacyTarget!,
                    subtitle: 'Hardware Sensor',
                    color: AuraTheme.warning,
                    onTap: onPrivacyClick,
                  ),
                  _buildConnector(),
                ],

                // Node 5: Behaviour / AI Deviation
                _buildNode(
                  icon: Icons.psychology_rounded,
                  category: 'BEHAVIOUR',
                  title: anomalyReason ?? 'Ensemble Anomaly',
                  subtitle: 'Dual ML Deviation',
                  color: Colors.orangeAccent,
                ),
                _buildConnector(),

                // Node 6: Synthesized Finding
                _buildNode(
                  icon: Icons.security_rounded,
                  category: 'FINDING',
                  title: findingTitle,
                  subtitle: '$severity Severity',
                  color: sevColor,
                  isHighlighted: true,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNode({
    required IconData icon,
    required String category,
    required String title,
    required String subtitle,
    required Color color,
    bool isHighlighted = false,
    VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        constraints: const BoxConstraints(minWidth: 150, maxWidth: 200),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isHighlighted ? color.withValues(alpha: 0.15) : AuraTheme.surface,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isHighlighted ? color : color.withValues(alpha: 0.4),
            width: isHighlighted ? 1.5 : 1.0,
          ),
          boxShadow: isHighlighted
              ? [BoxShadow(color: color.withValues(alpha: 0.2), blurRadius: 10, offset: const Offset(0, 2))]
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Icon(icon, size: 14, color: color),
                const SizedBox(width: 6),
                Text(
                  category,
                  style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: color, letterSpacing: 0.8),
                ),
                if (onTap != null) ...[
                  const Spacer(),
                  Icon(Icons.arrow_outward_rounded, size: 12, color: color.withValues(alpha: 0.8)),
                ],
              ],
            ),
            const SizedBox(height: 8),
            Text(
              title,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: const TextStyle(fontSize: 10, color: AuraTheme.textSecondary),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConnector() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Row(
        children: [
          Container(width: 14, height: 2, color: AuraTheme.border),
          const Icon(Icons.arrow_forward_ios_rounded, size: 10, color: AuraTheme.textSecondary),
        ],
      ),
    );
  }
}

