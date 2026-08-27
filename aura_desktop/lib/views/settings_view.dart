import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';

class SettingsView extends StatefulWidget {
  final VoidCallback? onReopenOnboarding;

  const SettingsView({super.key, this.onReopenOnboarding});

  @override
  State<SettingsView> createState() => _SettingsViewState();
}

class _SettingsViewState extends State<SettingsView> {
  int _settingsTab = 0; // 0: General, 1: Privacy, 2: Monitoring & AI, 3: Diagnostics, 4: About

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Navigation Tabs Header
          _buildTabsHeader(),
          const SizedBox(height: 24),

          // Active Settings Section
          if (_settingsTab == 0) _buildGeneralSection(state),
          if (_settingsTab == 1) _buildPrivacySection(state),
          if (_settingsTab == 2) _buildMonitoringSection(state),
          if (_settingsTab == 3) _buildDiagnosticsSection(state),
          if (_settingsTab == 4) _buildAboutSection(),
        ],
      ),
    );
  }

  Widget _buildTabsHeader() {
    final tabs = [
      {'label': 'General', 'icon': Icons.tune_rounded},
      {'label': 'Privacy & Sentinels', 'icon': Icons.shield_outlined},
      {'label': 'Monitoring & AI', 'icon': Icons.psychology_outlined},
      {'label': 'Advanced Diagnostics', 'icon': Icons.developer_board_rounded},
      {'label': 'About AURA', 'icon': Icons.info_outline_rounded},
    ];

    return Container(
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AuraTheme.borderSubtle)),
      ),
      child: Row(
        children: List.generate(tabs.length, (i) {
          final isSelected = _settingsTab == i;
          return InkWell(
            onTap: () => setState(() => _settingsTab = i),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
              decoration: BoxDecoration(
                border: Border(
                  bottom: BorderSide(
                    color: isSelected ? AuraTheme.primaryLight : Colors.transparent,
                    width: 2,
                  ),
                ),
              ),
              child: Row(
                children: [
                  Icon(tabs[i]['icon'] as IconData, size: 16, color: isSelected ? AuraTheme.primaryLight : AuraTheme.textSecondary),
                  const SizedBox(width: 8),
                  Text(
                    tabs[i]['label'] as String,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: isSelected ? FontWeight.w800 : FontWeight.w500,
                      color: isSelected ? AuraTheme.textPrimary : AuraTheme.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          );
        }),
      ),
    );
  }

  // -------------------------------------------------------------
  // TAB 0: GENERAL
  // -------------------------------------------------------------
  Widget _buildGeneralSection(AuraStateProvider state) {
    return Column(
      children: [
        AuraCard(
          title: 'General Engine & Operator Preferences',
          icon: Icons.tune_rounded,
          child: Column(
            children: [
              _buildSettingRow(
                title: 'Sensor Sampling Cadence',
                subtitle: 'Rate at which background sensors inspect CPU, memory, and active processes.',
                value: '1.0s (Nominal Continuous)',
              ),
              const Divider(height: 24, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'Desktop Shell Theme Mode',
                subtitle: 'Cybersecurity dark visual theme with accessible contrast and Inter typography.',
                value: 'Dark Obsidian (Enforced)',
              ),
              const Divider(height: 24, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'Local Audit Retention Policy',
                subtitle: 'Automatic pruning of historical events older than the retention window.',
                value: '30 Days (SQLite WAL)',
              ),
            ],
          ),
        ),
      ],
    );
  }

  // -------------------------------------------------------------
  // TAB 1: PRIVACY & SENTINELS
  // -------------------------------------------------------------
  Widget _buildPrivacySection(AuraStateProvider state) {
    return Column(
      children: [
        AuraCard(
          title: 'Hardware Privacy Sentinel Policies',
          icon: Icons.shield_rounded,
          child: Column(
            children: [
              _buildSettingRow(
                title: 'Zero-Media Capture Enforcement',
                subtitle: 'Strict policy guarantee: raw webcam video and microphone audio are never recorded or stored.',
                value: 'ACTIVE & ENFORCED',
                valueColor: AuraTheme.healthy,
              ),
              const Divider(height: 24, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'Windows Consent Registry Tracking',
                subtitle: 'CapabilityAccessManager tracking for Camera and Microphone sensor access.',
                value: 'POLLING ACTIVE',
              ),
              const Divider(height: 24, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'Direct Windows Privacy Shortcuts',
                subtitle: 'Quick launchers to configure Windows 11 camera and microphone permission toggles.',
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    OutlinedButton(
                      onPressed: () => state.openShortcut('CAMERA'),
                      child: const Text('CAMERA SETTINGS', style: TextStyle(fontSize: 10)),
                    ),
                    const SizedBox(width: 8),
                    OutlinedButton(
                      onPressed: () => state.openShortcut('MICROPHONE'),
                      child: const Text('MIC SETTINGS', style: TextStyle(fontSize: 10)),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // -------------------------------------------------------------
  // TAB 2: MONITORING & AI
  // -------------------------------------------------------------
  Widget _buildMonitoringSection(AuraStateProvider state) {
    return Column(
      children: [
        AuraCard(
          title: 'Monitoring & Machine Learning Architecture',
          icon: Icons.psychology_rounded,
          child: Column(
            children: [
              _buildSettingRow(
                title: 'Process DNA Profiler Engine',
                subtitle: 'Extracts cryptographic SHA-256 binary digests and parent-child execution hierarchies.',
                value: 'ACTIVE',
                valueColor: AuraTheme.healthy,
              ),
              const Divider(height: 24, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'AI Anomaly Ensemble Mode',
                subtitle: 'Dual-model Isolation Forest and Local Outlier Factor (LOF) evaluating 10-D feature vectors.',
                value: 'UNSUPERVISED ENSEMBLE',
              ),
              const Divider(height: 24, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'Network Attack Surface Classifier',
                subtitle: 'Classifies local socket flows into Public WAN vs Private LAN without packet inspection.',
                value: 'PASSIVE CLASSIFICATION',
              ),
            ],
          ),
        ),
      ],
    );
  }

  // -------------------------------------------------------------
  // TAB 3: ADVANCED DIAGNOSTICS
  // -------------------------------------------------------------
  Widget _buildDiagnosticsSection(AuraStateProvider state) {
    return Column(
      children: [
        AuraCard(
          title: 'Advanced System & Service Diagnostics',
          icon: Icons.developer_board_rounded,
          child: Column(
            children: [
              _buildSettingRow(
                title: 'Local Security Engine Link',
                subtitle: 'Loopback API endpoint and real-time WebSocket telemetry stream.',
                value: 'http://127.0.0.1:8787 (WS Live)',
                valueColor: state.isAuthenticated ? AuraTheme.healthy : AuraTheme.critical,
              ),
              const Divider(height: 24, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'Local Storage Engine',
                subtitle: 'Encrypted SQLite database with Write-Ahead Logging (WAL) and integrity verification.',
                value: 'data/aura.db (WAL Mode)',
              ),
              const Divider(height: 24, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'Operator Onboarding & Capability Guide',
                subtitle: 'Re-run the initial 5-stage setup, privacy promise, and system readiness walkthrough.',
                trailing: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(backgroundColor: AuraTheme.primary),
                  onPressed: widget.onReopenOnboarding,
                  icon: const Icon(Icons.replay_rounded, size: 14),
                  label: const Text('OPEN CAPABILITY CENTER', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // -------------------------------------------------------------
  // TAB 4: ABOUT
  // -------------------------------------------------------------
  Widget _buildAboutSection() {
    return Column(
      children: [
        AuraCard(
          title: 'About AURA Privacy Guardian',
          icon: Icons.info_outline_rounded,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.shield_rounded, color: AuraTheme.primaryLight, size: 28),
                  SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('AURA — Privacy Guardian', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: AuraTheme.textPrimary)),
                      Text('Version 2.0.0 (Flagship Release)', style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary)),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Text(
                'AURA is an AI-Powered Real-Time Privacy Intelligence and Intrusion Detection System built for Windows. It unifies Windows security posture, hardware privacy sentinels, process execution DNA, network socket analysis, and explainable machine learning into an integrated security platform for your PC.',
                style: TextStyle(fontSize: 13, height: 1.5, color: AuraTheme.textPrimary),
              ),
              const SizedBox(height: 16),
              _buildSettingRow(
                title: 'Core Architecture',
                subtitle: 'Loopback-isolated FastAPI engine (`127.0.0.1:8787`) + Native Flutter Windows desktop shell.',
                value: 'HYBRID NATIVE',
              ),
              const Divider(height: 20, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'Process Intelligence & DNA',
                subtitle: 'Extracts cryptographic SHA-256 digests, parent-child hierarchies, handles, and network flows.',
                value: 'ENABLED',
                valueColor: AuraTheme.healthy,
              ),
              const Divider(height: 20, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'Machine Learning Model',
                subtitle: 'Dual-model unsupervised anomaly detection: Isolation Forest (100 trees) + Local Outlier Factor (LOF).',
                value: 'IFOREST + LOF',
              ),
              const Divider(height: 20, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'SPL Clarification',
                subtitle: 'AURA relies strictly on standard Windows Win32, Registry, and ETW telemetry primitives—no black-box proprietary language.',
                value: 'STANDARD WIN32',
              ),
              const Divider(height: 20, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'Privacy & Data Protection',
                subtitle: 'Zero-Media Capture Guarantee: webcam frames and microphone audio waveforms are never recorded or written to disk.',
                value: 'ZERO-MEDIA ENFORCED',
                valueColor: AuraTheme.healthy,
              ),
              const Divider(height: 20, color: AuraTheme.borderSubtle),
              _buildSettingRow(
                title: 'Security Boundaries',
                subtitle: 'AURA is an intelligence and anomaly detection engine; it does not replace kernel-level EDR or perform disk malware deletion.',
                value: 'INTELLIGENCE ONLY',
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AuraTheme.healthy.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AuraTheme.healthy.withValues(alpha: 0.3)),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.verified_rounded, size: 16, color: AuraTheme.healthy),
                    SizedBox(width: 8),
                    Text(
                      '100% Local-First Architecture • Zero External Cloud Telemetry Leakage',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AuraTheme.healthy),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSettingRow({
    required String title,
    required String subtitle,
    String? value,
    Color? valueColor,
    Widget? trailing,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
              const SizedBox(height: 2),
              Text(subtitle, style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary, height: 1.3)),
            ],
          ),
        ),
        const SizedBox(width: 16),
        if (trailing != null)
          trailing
        else if (value != null)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AuraTheme.surfaceElevated,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: AuraTheme.borderSubtle),
            ),
            child: Text(
              value,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: valueColor ?? AuraTheme.primaryLight,
              ),
            ),
          ),
      ],
    );
  }
}
