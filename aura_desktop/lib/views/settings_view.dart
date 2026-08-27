import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';

class SettingsView extends StatelessWidget {
  const SettingsView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AuraCard(
            title: 'Agent Preferences & Engine Policy Configuration',
            icon: Icons.settings_rounded,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _SettingRow(
                  title: 'Real-Time Sensor Sampling Cadence',
                  subtitle: 'Engine polls hardware and process metrics every 1.0s in background.',
                  value: '1.0s (Nominal)',
                ),
                const SizedBox(height: 12),
                _SettingRow(
                  title: 'Zero-Media Privacy Policy',
                  subtitle: 'Strict enforcement: no raw video frames or microphone audio stored on disk.',
                  value: 'ENFORCED',
                ),
                const SizedBox(height: 12),
                _SettingRow(
                  title: 'Machine Learning Ensemble Mode',
                  subtitle: 'Unsupervised Isolation Forest + Local Outlier Factor (LOF) anomaly detection.',
                  value: 'ONLINE',
                ),
                const SizedBox(height: 12),
                _SettingRow(
                  title: 'Local API Endpoint & WebSocket Stream',
                  subtitle: 'Communicating over local loopback with Bearer token authentication.',
                  value: 'http://127.0.0.1:8787',
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Windows Shortcuts Quick Actions
          AuraCard(
            title: 'Direct Windows System Security Shortcuts',
            icon: Icons.launch_rounded,
            child: Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(backgroundColor: AuraTheme.surfaceElevated, foregroundColor: Colors.white),
                  onPressed: () => state.openShortcut('CAMERA'),
                  icon: const Icon(Icons.videocam_rounded, size: 16),
                  label: const Text('Camera Privacy Settings'),
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(backgroundColor: AuraTheme.surfaceElevated, foregroundColor: Colors.white),
                  onPressed: () => state.openShortcut('MICROPHONE'),
                  icon: const Icon(Icons.mic_rounded, size: 16),
                  label: const Text('Microphone Privacy Settings'),
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(backgroundColor: AuraTheme.surfaceElevated, foregroundColor: Colors.white),
                  onPressed: () => state.openShortcut('DEFENDER'),
                  icon: const Icon(Icons.security_rounded, size: 16),
                  label: const Text('Windows Security Dashboard'),
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(backgroundColor: AuraTheme.surfaceElevated, foregroundColor: Colors.white),
                  onPressed: () => state.openShortcut('FIREWALL'),
                  icon: const Icon(Icons.local_fire_department_rounded, size: 16),
                  label: const Text('Windows Defender Firewall'),
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(backgroundColor: AuraTheme.surfaceElevated, foregroundColor: Colors.white),
                  onPressed: () => state.openShortcut('UPDATE'),
                  icon: const Icon(Icons.system_update_rounded, size: 16),
                  label: const Text('Windows Update Settings'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SettingRow extends StatelessWidget {
  final String title;
  final String subtitle;
  final String value;

  const _SettingRow({required this.title, required this.subtitle, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AuraTheme.textPrimary)),
              Text(subtitle, style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: AuraTheme.surfaceElevated,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: AuraTheme.borderSubtle),
          ),
          child: Text(value, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AuraTheme.primaryLight)),
        ),
      ],
    );
  }
}
