import 'package:flutter/material.dart';
import '../core/theme/aura_theme.dart';

class AuraStatusBadge extends StatelessWidget {
  final String status; // OBSERVED, INFERRED, SUSPECTED, UNKNOWN, PROTECTED, ATTENTION, CRITICAL, READY, ACTIVE, LIMITED
  final double fontSize;

  const AuraStatusBadge({
    super.key,
    required this.status,
    this.fontSize = 11,
  });

  @override
  Widget build(BuildContext context) {
    Color color;
    IconData? icon;

    switch (status.toUpperCase()) {
      case 'PROTECTED':
      case 'OBSERVED':
      case 'READY':
      case 'ACTIVE':
      case 'HEALTHY':
        color = AuraTheme.healthy;
        icon = Icons.check_circle_outline_rounded;
        break;
      case 'INFERRED':
      case 'ATTENTION':
      case 'LIMITED':
      case 'MEDIUM':
      case 'WARNING':
        color = AuraTheme.warning;
        icon = Icons.info_outline_rounded;
        break;
      case 'SUSPECTED':
      case 'CRITICAL':
      case 'HIGH':
      case 'INVESTIGATION REQUIRED':
      case 'FAILED':
        color = AuraTheme.critical;
        icon = Icons.warning_amber_rounded;
        break;
      case 'UNKNOWN':
      default:
        color = AuraTheme.textSecondary;
        icon = Icons.help_outline_rounded;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: fontSize + 1, color: color),
          const SizedBox(width: 4),
          Text(
            status.toUpperCase(),
            style: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.w800,
              color: color,
              letterSpacing: 0.6,
            ),
          ),
        ],
      ),
    );
  }
}
