import 'package:flutter/material.dart';
import '../core/theme/aura_theme.dart';

class SeverityBadge extends StatelessWidget {
  final String severity;
  final bool compact;

  const SeverityBadge({
    super.key,
    required this.severity,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    final s = severity.toUpperCase();
    Color bg;
    Color fg;
    IconData icon;

    switch (s) {
      case 'CRITICAL':
        bg = AuraTheme.critical.withValues(alpha: 0.15);
        fg = AuraTheme.critical;
        icon = Icons.error_rounded;
        break;
      case 'HIGH':
        bg = AuraTheme.high.withValues(alpha: 0.15);
        fg = AuraTheme.high;
        icon = Icons.warning_rounded;
        break;
      case 'MEDIUM':
        bg = AuraTheme.medium.withValues(alpha: 0.15);
        fg = AuraTheme.medium;
        icon = Icons.report_problem_rounded;
        break;
      case 'LOW':
        bg = AuraTheme.low.withValues(alpha: 0.15);
        fg = AuraTheme.low;
        icon = Icons.info_rounded;
        break;
      default:
        bg = AuraTheme.info.withValues(alpha: 0.15);
        fg = AuraTheme.info;
        icon = Icons.circle_outlined;
        break;
    }

    return Container(
      padding: EdgeInsets.symmetric(horizontal: compact ? 6 : 8, vertical: compact ? 2 : 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: fg.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: compact ? 10 : 12, color: fg),
          const SizedBox(width: 4),
          Text(
            s,
            style: TextStyle(
              fontSize: compact ? 10 : 11,
              fontWeight: FontWeight.w700,
              color: fg,
              letterSpacing: 0.6,
            ),
          ),
        ],
      ),
    );
  }
}
