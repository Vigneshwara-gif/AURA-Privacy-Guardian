import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../core/utils/formatters.dart';
import '../models/privacy.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/metric_gauge.dart';

class PrivacySentinelView extends StatelessWidget {
  const PrivacySentinelView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final priv = state.privacySummary;
    final cam = priv?.camera;
    final mic = priv?.microphone;
    final privScore = priv?.overallPrivacyScore ?? 100;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Zero-Media Capture & Privacy Score Banner
          _buildZeroMediaBanner(state, privScore),
          const SizedBox(height: 24),

          // 2. Camera Sentinel Deep Intelligence Card
          _buildCameraSentinelCard(context, state, cam),
          const SizedBox(height: 24),

          // 3. Microphone Sentinel Deep Intelligence Card
          _buildMicrophoneSentinelCard(context, state, mic),
          const SizedBox(height: 24),

          // 4. Windows Privacy Consent Architecture Note
          _buildPrivacyArchitectureNote(),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // ZERO-MEDIA CAPTURE & PRIVACY HEALTH BANNER
  // -------------------------------------------------------------
  Widget _buildZeroMediaBanner(AuraStateProvider state, int privScore) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AuraTheme.surfaceElevated,
            AuraTheme.accentTeal.withValues(alpha: 0.1),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AuraTheme.accentTeal.withValues(alpha: 0.35)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AuraTheme.accentTeal.withValues(alpha: 0.15),
              shape: BoxShape.circle,
              border: Border.all(color: AuraTheme.accentTeal.withValues(alpha: 0.5)),
            ),
            child: const Icon(Icons.shield_rounded, color: AuraTheme.accentTeal, size: 32),
          ),
          const SizedBox(width: 20),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      'ZERO-MEDIA CAPTURE PRIVACY GUARANTEE',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w900,
                        color: AuraTheme.accentTeal,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 6),
                Text(
                  'AURA inspects Windows CapabilityAccessManager metadata, device setup classes, and process handles.\nAURA NEVER records microphone audio, captures webcam frames, or stores raw media on disk.',
                  style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary, height: 1.4),
                ),
              ],
            ),
          ),
          const SizedBox(width: 20),
          SizedBox(
            width: 150,
            child: ScoreMetricGauge(
              label: 'Privacy Score',
              score: privScore,
              subtitle: 'Camera & Mic consent',
              color: AuraTheme.accentTeal,
            ),
          ),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // CAMERA SENTINEL CARD
  // -------------------------------------------------------------
  Widget _buildCameraSentinelCard(BuildContext context, AuraStateProvider state, CameraIntelligence? cam) {
    final hasDevices = (cam?.devices.isNotEmpty ?? false);
    final isActive = cam?.isActive ?? false;
    final isAllowed = cam?.systemPermission == 'ALLOWED';

    String stateBadgeText;
    Color stateBadgeColor;
    if (cam == null) {
      stateBadgeText = 'CHECKING SENSORS...';
      stateBadgeColor = AuraTheme.warning;
    } else if (!hasDevices) {
      stateBadgeText = 'NO CAMERA DETECTED';
      stateBadgeColor = AuraTheme.textMuted;
    } else if (!isAllowed) {
      stateBadgeText = 'PERMISSION DENIED';
      stateBadgeColor = AuraTheme.critical;
    } else if (isActive) {
      stateBadgeText = 'ACTIVE SESSION';
      stateBadgeColor = AuraTheme.critical;
    } else {
      stateBadgeText = 'DEVICE READY & IDLE';
      stateBadgeColor = AuraTheme.healthy;
    }

    return AuraCard(
      title: 'Camera Device Intelligence & Session Attribution',
      icon: Icons.videocam_rounded,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildSentinelStatusBadge(stateBadgeText, stateBadgeColor),
          const SizedBox(width: 12),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              side: const BorderSide(color: AuraTheme.border),
            ),
            onPressed: () => state.openShortcut('CAMERA'),
            icon: const Icon(Icons.settings_rounded, size: 14),
            label: const Text('WINDOWS SETTINGS', style: TextStyle(fontSize: 11)),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            cam?.detail ?? 'Querying Windows CapabilityAccessManager and SetupAPI camera devices...',
            style: const TextStyle(fontSize: 13, color: AuraTheme.textPrimary),
          ),
          const SizedBox(height: 16),

          // Devices Inventory Table
          const Text(
            'Enumerated Camera Hardware Devices:',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary),
          ),
          const SizedBox(height: 8),
          if (cam?.devices.isEmpty ?? true)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AuraTheme.surfaceElevated,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Text('No physical camera hardware devices reported by Windows PnP subsystem.', style: TextStyle(fontSize: 12, color: AuraTheme.textMuted)),
            )
          else
            ...cam!.devices.map((d) => Container(
                  margin: const EdgeInsets.only(bottom: 6),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AuraTheme.surfaceElevated,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AuraTheme.borderSubtle),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.camera_alt_rounded, size: 16, color: AuraTheme.primaryLight),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(d.name, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AuraTheme.textPrimary)),
                      ),
                      Text('Driver: ${d.driverVersion}', style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
                      const SizedBox(width: 12),
                      Text('(${d.provider})', style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
                    ],
                  ),
                )),
          const SizedBox(height: 16),

          // Recent App Access History
          const Text(
            'Recent Application Access History (Windows Consent Store):',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary),
          ),
          const SizedBox(height: 8),
          if (cam?.recentUsage.isEmpty ?? true)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: Text('Zero recent camera access events registered.', style: TextStyle(fontSize: 12, color: AuraTheme.textMuted)),
            )
          else
            ...cam!.recentUsage.take(5).map((u) => Container(
                  margin: const EdgeInsets.only(bottom: 6),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: u.isCurrentlyActive ? AuraTheme.critical.withValues(alpha: 0.1) : AuraTheme.surfaceElevated,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: u.isCurrentlyActive ? AuraTheme.critical.withValues(alpha: 0.4) : AuraTheme.borderSubtle),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        u.isCurrentlyActive ? Icons.radio_button_checked_rounded : Icons.history_rounded,
                        size: 14,
                        color: u.isCurrentlyActive ? AuraTheme.critical : AuraTheme.textMuted,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          '${u.appName} (${u.isPackaged ? "UWP Package" : "Win32 Executable"})',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: u.isCurrentlyActive ? FontWeight.w800 : FontWeight.w500,
                            color: u.isCurrentlyActive ? AuraTheme.critical : AuraTheme.textPrimary,
                          ),
                        ),
                      ),
                      Text(
                        u.isCurrentlyActive ? 'CAPTURING LIVE' : 'Accessed: ${Formatters.formatIso(u.lastUsedStart)}',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: u.isCurrentlyActive ? FontWeight.w700 : FontWeight.w400,
                          color: u.isCurrentlyActive ? AuraTheme.critical : AuraTheme.textMuted,
                        ),
                      ),
                    ],
                  ),
                )),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // MICROPHONE SENTINEL CARD
  // -------------------------------------------------------------
  Widget _buildMicrophoneSentinelCard(BuildContext context, AuraStateProvider state, MicrophoneIntelligence? mic) {
    final hasDevices = (mic?.devices.isNotEmpty ?? false);
    final isActive = mic?.isActive ?? false;
    final isAllowed = mic?.systemPermission == 'ALLOWED';

    String stateBadgeText;
    Color stateBadgeColor;
    if (mic == null) {
      stateBadgeText = 'CHECKING SENSORS...';
      stateBadgeColor = AuraTheme.warning;
    } else if (!hasDevices) {
      stateBadgeText = 'NO MICROPHONE DETECTED';
      stateBadgeColor = AuraTheme.textMuted;
    } else if (!isAllowed) {
      stateBadgeText = 'PERMISSION DENIED';
      stateBadgeColor = AuraTheme.critical;
    } else if (isActive) {
      stateBadgeText = 'ACTIVE AUDIO STREAM';
      stateBadgeColor = AuraTheme.critical;
    } else {
      stateBadgeText = 'ENDPOINT READY & IDLE';
      stateBadgeColor = AuraTheme.healthy;
    }

    return AuraCard(
      title: 'Microphone Audio Sentinel & Active Stream Attribution',
      icon: Icons.mic_rounded,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildSentinelStatusBadge(stateBadgeText, stateBadgeColor),
          const SizedBox(width: 12),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              side: const BorderSide(color: AuraTheme.border),
            ),
            onPressed: () => state.openShortcut('MICROPHONE'),
            icon: const Icon(Icons.settings_rounded, size: 14),
            label: const Text('WINDOWS SETTINGS', style: TextStyle(fontSize: 11)),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            mic?.detail ?? 'Querying Windows MMDevice API and audio endpoint streams...',
            style: const TextStyle(fontSize: 13, color: AuraTheme.textPrimary),
          ),
          const SizedBox(height: 16),

          // Endpoints Table
          const Text(
            'Enumerated Audio Capture Endpoints:',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary),
          ),
          const SizedBox(height: 8),
          if (mic?.devices.isEmpty ?? true)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AuraTheme.surfaceElevated,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Text('No active audio capture endpoints reported.', style: TextStyle(fontSize: 12, color: AuraTheme.textMuted)),
            )
          else
            ...mic!.devices.map((d) => Container(
                  margin: const EdgeInsets.only(bottom: 6),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AuraTheme.surfaceElevated,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AuraTheme.borderSubtle),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.mic_none_rounded, size: 16, color: AuraTheme.primaryLight),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(d.name, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AuraTheme.textPrimary)),
                      ),
                      Text('Driver: ${d.driverVersion}', style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
                      const SizedBox(width: 12),
                      Text('(${d.provider})', style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
                    ],
                  ),
                )),
          const SizedBox(height: 16),

          // Recent Usage Table
          const Text(
            'Recent Microphone Access History (Windows Consent Store):',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary),
          ),
          const SizedBox(height: 8),
          if (mic?.recentUsage.isEmpty ?? true)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: Text('Zero recent audio capture events registered.', style: TextStyle(fontSize: 12, color: AuraTheme.textMuted)),
            )
          else
            ...mic!.recentUsage.take(5).map((u) => Container(
                  margin: const EdgeInsets.only(bottom: 6),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: u.isCurrentlyActive ? AuraTheme.critical.withValues(alpha: 0.1) : AuraTheme.surfaceElevated,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: u.isCurrentlyActive ? AuraTheme.critical.withValues(alpha: 0.4) : AuraTheme.borderSubtle),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        u.isCurrentlyActive ? Icons.graphic_eq_rounded : Icons.history_rounded,
                        size: 14,
                        color: u.isCurrentlyActive ? AuraTheme.critical : AuraTheme.textMuted,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          '${u.appName} (${u.isPackaged ? "UWP Package" : "Win32 Executable"})',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: u.isCurrentlyActive ? FontWeight.w800 : FontWeight.w500,
                            color: u.isCurrentlyActive ? AuraTheme.critical : AuraTheme.textPrimary,
                          ),
                        ),
                      ),
                      Text(
                        u.isCurrentlyActive ? 'AUDIO STREAM ACTIVE' : 'Accessed: ${Formatters.formatIso(u.lastUsedStart)}',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: u.isCurrentlyActive ? FontWeight.w700 : FontWeight.w400,
                          color: u.isCurrentlyActive ? AuraTheme.critical : AuraTheme.textMuted,
                        ),
                      ),
                    ],
                  ),
                )),
        ],
      ),
    );
  }

  Widget _buildSentinelStatusBadge(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 6, height: 6, decoration: BoxDecoration(shape: BoxShape.circle, color: color)),
          const SizedBox(width: 6),
          Text(
            text,
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: color, letterSpacing: 0.6),
          ),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // PRIVACY ARCHITECTURE NOTE
  // -------------------------------------------------------------
  Widget _buildPrivacyArchitectureNote() {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.25),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AuraTheme.borderSubtle),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.lock_clock_rounded, size: 18, color: AuraTheme.accentTeal),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Windows Privacy Consent & Hardware Sentinel Architecture',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                ),
                SizedBox(height: 4),
                Text(
                  'AURA uses non-intrusive Windows APIs to monitor sensor state transitions. When an app requests the camera or microphone, Windows records access metadata in the CapabilityAccessManager registry. AURA reads this telemetry to alert you of background access without intercepting the audio/video streams.',
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
