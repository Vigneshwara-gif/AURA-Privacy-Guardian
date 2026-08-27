import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../core/utils/formatters.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';

class PrivacySentinelView extends StatelessWidget {
  const PrivacySentinelView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final priv = state.privacySummary;
    final cam = priv?.camera;
    final mic = priv?.microphone;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Disclaimer & Privacy Score Banner
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AuraTheme.surfaceElevated,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AuraTheme.accentTeal.withValues(alpha: 0.3)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AuraTheme.accentTeal.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.privacy_tip_rounded, color: AuraTheme.accentTeal, size: 28),
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'ZERO-MEDIA CAPTURE HARDWARE SENTINELS',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: AuraTheme.accentTeal, letterSpacing: 1.0),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'AURA monitors Windows CapabilityAccessManager metadata, setup classes, and process handles. AURA NEVER captures or records raw video frames or microphone audio.',
                        style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
                      ),
                    ],
                  ),
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(backgroundColor: AuraTheme.surfaceHighlight, foregroundColor: Colors.white),
                  onPressed: () => state.openShortcut('CAMERA'),
                  icon: const Icon(Icons.settings_rounded, size: 14),
                  label: const Text('WINDOWS PRIVACY SETTINGS', style: TextStyle(fontSize: 11)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Camera Sentinel Card
          if (cam != null) ...[
            AuraCard(
              title: 'Camera Device Intelligence & Session Attribution',
              icon: Icons.videocam_rounded,
              trailing: _StatusPill(isActive: cam.isActive, isAllowed: cam.systemPermission == 'ALLOWED'),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(cam.detail, style: const TextStyle(fontSize: 13, color: AuraTheme.textPrimary)),
                  const SizedBox(height: 16),
                  const Text('Enumerated Camera Hardware Devices:',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary)),
                  const SizedBox(height: 8),
                  ...cam.devices.map((d) => Container(
                        margin: const EdgeInsets.only(bottom: 6),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AuraTheme.surfaceElevated,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: AuraTheme.borderSubtle),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.camera_alt_rounded, size: 16, color: AuraTheme.primaryLight),
                            const SizedBox(width: 10),
                            Expanded(child: Text(d.name, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600))),
                            Text('Driver: ${d.driverVersion} (${d.provider})', style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
                          ],
                        ),
                      )),
                  const SizedBox(height: 16),
                  const Text('Recent Application Access History:',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary)),
                  const SizedBox(height: 8),
                  if (cam.recentUsage.isEmpty)
                    const Text('No recent camera usage records logged.', style: TextStyle(fontSize: 12, color: AuraTheme.textMuted))
                  else
                    ...cam.recentUsage.take(5).map((u) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(
                            children: [
                              Icon(Icons.history_rounded, size: 14, color: u.isCurrentlyActive ? AuraTheme.critical : AuraTheme.textMuted),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  '${u.appName} (${u.isPackaged ? "UWP" : "Win32"})',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: u.isCurrentlyActive ? FontWeight.w700 : FontWeight.w500,
                                    color: u.isCurrentlyActive ? AuraTheme.critical : AuraTheme.textPrimary,
                                  ),
                                ),
                              ),
                              Text('Started: ${Formatters.formatIso(u.lastUsedStart)}', style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
                            ],
                          ),
                        )),
                ],
              ),
            ),
            const SizedBox(height: 24),
          ],

          // Microphone Sentinel Card
          if (mic != null) ...[
            AuraCard(
              title: 'Microphone Audio Sentinel & Active Stream Attribution',
              icon: Icons.mic_rounded,
              trailing: _StatusPill(isActive: mic.isActive, isAllowed: mic.systemPermission == 'ALLOWED'),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(mic.detail, style: const TextStyle(fontSize: 13, color: AuraTheme.textPrimary)),
                  const SizedBox(height: 16),
                  Text('Discovered Audio Capture Endpoints (${mic.deviceCount}):',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary)),
                  const SizedBox(height: 8),
                  ...mic.devices.take(6).map((d) => Container(
                        margin: const EdgeInsets.only(bottom: 6),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AuraTheme.surfaceElevated,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: AuraTheme.borderSubtle),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.graphic_eq_rounded, size: 16, color: AuraTheme.accentTeal),
                            const SizedBox(width: 10),
                            Expanded(child: Text(d.name, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600))),
                            Text('Driver: ${d.driverVersion}', style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
                          ],
                        ),
                      )),
                  const SizedBox(height: 16),
                  const Text('Recent Audio Access History:',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary)),
                  const SizedBox(height: 8),
                  if (mic.recentUsage.isEmpty)
                    const Text('No recent audio capture sessions logged.', style: TextStyle(fontSize: 12, color: AuraTheme.textMuted))
                  else
                    ...mic.recentUsage.take(5).map((u) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(
                            children: [
                              Icon(Icons.history_rounded, size: 14, color: u.isCurrentlyActive ? AuraTheme.critical : AuraTheme.textMuted),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  '${u.appName} (${u.isPackaged ? "UWP" : "Win32"})',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: u.isCurrentlyActive ? FontWeight.w700 : FontWeight.w500,
                                    color: u.isCurrentlyActive ? AuraTheme.critical : AuraTheme.textPrimary,
                                  ),
                                ),
                              ),
                              Text('Started: ${Formatters.formatIso(u.lastUsedStart)}', style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
                            ],
                          ),
                        )),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  final bool isActive;
  final bool isAllowed;

  const _StatusPill({required this.isActive, required this.isAllowed});

  @override
  Widget build(BuildContext context) {
    if (isActive) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: AuraTheme.critical.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12), border: Border.all(color: AuraTheme.critical)),
        child: const Text('STREAMING ACTIVE', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: AuraTheme.critical)),
      );
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: AuraTheme.healthy.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12), border: Border.all(color: AuraTheme.healthy)),
      child: Text(isAllowed ? 'MONITORED (IDLE)' : 'PERMISSION DENIED',
          style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: isAllowed ? AuraTheme.healthy : AuraTheme.medium)),
    );
  }
}
