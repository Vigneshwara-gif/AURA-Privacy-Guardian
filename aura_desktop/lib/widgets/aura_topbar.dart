import 'package:flutter/material.dart';
import '../core/theme/aura_theme.dart';

class AuraTopbar extends StatelessWidget {
  final String title;
  final VoidCallback onQuickScan;
  final VoidCallback onAlertsTap;
  final int alertCount;
  final bool isScanning;
  final String connectionState;

  const AuraTopbar({
    super.key,
    required this.title,
    required this.onQuickScan,
    required this.onAlertsTap,
    this.alertCount = 0,
    this.isScanning = false,
    this.connectionState = 'LIVE',
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      decoration: const BoxDecoration(
        color: AuraTheme.surface,
        border: Border(bottom: BorderSide(color: AuraTheme.border, width: 1)),
      ),
      child: Row(
        children: [
          // Section Title
          Text(
            title,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: AuraTheme.textPrimary,
            ),
          ),
          const SizedBox(width: 16),

          // Live Connection Status Pill
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AuraTheme.healthy.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AuraTheme.healthy.withValues(alpha: 0.3)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 6,
                  height: 6,
                  decoration: const BoxDecoration(
                    color: AuraTheme.healthy,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  connectionState,
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: AuraTheme.healthy,
                    letterSpacing: 0.8,
                  ),
                ),
              ],
            ),
          ),

          const Spacer(),

          // Quick Full Scan CTA Button
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: AuraTheme.primary,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            onPressed: isScanning ? null : onQuickScan,
            icon: isScanning
                ? const SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                  )
                : const Icon(Icons.radar_rounded, size: 16),
            label: Text(
              isScanning ? 'SCANNING SYSTEM...' : 'RUN FULL SCAN',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 0.8),
            ),
          ),
          const SizedBox(width: 16),

          // Alert Notification Bell with Badge
          Stack(
            clipBehavior: Clip.none,
            children: [
              IconButton(
                icon: const Icon(Icons.notifications_none_rounded, color: AuraTheme.textSecondary),
                onPressed: onAlertsTap,
                tooltip: 'Security Alerts',
              ),
              if (alertCount > 0)
                Positioned(
                  top: 8,
                  right: 8,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                      color: AuraTheme.critical,
                      shape: BoxShape.circle,
                    ),
                    child: Text(
                      alertCount > 9 ? '9+' : '$alertCount',
                      style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: Colors.white),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
