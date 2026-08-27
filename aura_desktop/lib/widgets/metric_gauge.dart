import 'package:flutter/material.dart';
import '../core/theme/aura_theme.dart';

class ScoreMetricGauge extends StatelessWidget {
  final String label;
  final int score;
  final String subtitle;
  final Color? color;

  const ScoreMetricGauge({
    super.key,
    required this.label,
    required this.score,
    required this.subtitle,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    Color barColor = color ??
        (score >= 80
            ? AuraTheme.healthy
            : score >= 50
                ? AuraTheme.medium
                : AuraTheme.critical);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                label,
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AuraTheme.textSecondary),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              '$score/100',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: barColor),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: (score / 100).clamp(0.0, 1.0),
            minHeight: 6,
            backgroundColor: AuraTheme.border,
            valueColor: AlwaysStoppedAnimation<Color>(barColor),
          ),
        ),
        const SizedBox(height: 6),
        Text(
          subtitle,
          style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted),
        ),
      ],
    );
  }
}
