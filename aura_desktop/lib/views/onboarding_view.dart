import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../state/aura_state_provider.dart';

class OnboardingView extends StatefulWidget {
  final VoidCallback onFinish;

  const OnboardingView({super.key, required this.onFinish});

  @override
  State<OnboardingView> createState() => _OnboardingViewState();
}

class _OnboardingViewState extends State<OnboardingView> {
  int _currentStep = 0;
  bool _isConnecting = false;
  String? _connectError;
  bool _sessionConnected = false;

  void _nextStep() {
    setState(() {
      _currentStep++;
    });
  }

  void _prevStep() {
    if (_currentStep > 0) {
      setState(() {
        _currentStep--;
      });
    }
  }

  void _connectAgent(AuraStateProvider state) async {
    setState(() {
      _isConnecting = true;
      _connectError = null;
    });

    final ok = await state.authenticate('LOCAL_OPERATOR_DEV_SESSION');

    if (mounted) {
      setState(() {
        _isConnecting = false;
        if (ok) {
          _sessionConnected = true;
          _currentStep = 2; // Proceed to Privacy Promise
        } else {
          _connectError = state.errorMessage ??
              'Unable to establish local secure session with AURA Security Engine (127.0.0.1:8787). Ensure background service is running.';
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();

    return Scaffold(
      backgroundColor: AuraTheme.background,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 24),
          child: Container(
            constraints: const BoxConstraints(maxWidth: 920),
            decoration: BoxDecoration(
              color: AuraTheme.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AuraTheme.border),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.45),
                  blurRadius: 36,
                  offset: const Offset(0, 12),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Step Indicator Header
                  _buildHeaderProgress(),
                  const Divider(height: 1, color: AuraTheme.borderSubtle),

                  // Step Content
                  Padding(
                    padding: const EdgeInsets.all(36),
                    child: _buildStepContent(state),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeaderProgress() {
    const steps = [
      'Welcome',
      'Local Session',
      'Privacy Promise',
      'Capability Center',
      'System Readiness',
    ];

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      color: AuraTheme.surfaceElevated,
      width: double.infinity,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(steps.length, (index) {
            final isPassed = _currentStep > index;
            final isCurrent = _currentStep == index;

            return Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 26,
                  height: 26,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isPassed
                        ? AuraTheme.healthy
                        : isCurrent
                            ? AuraTheme.primaryLight
                            : AuraTheme.surface,
                    border: Border.all(
                      color: isPassed
                          ? AuraTheme.healthy
                          : isCurrent
                              ? AuraTheme.primaryLight
                              : AuraTheme.border,
                      width: 1.5,
                    ),
                  ),
                  child: Center(
                    child: isPassed
                        ? const Icon(Icons.check, size: 14, color: Colors.black)
                        : Text(
                            '${index + 1}',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: isCurrent ? Colors.black : AuraTheme.textSecondary,
                            ),
                          ),
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  steps[index],
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: isCurrent ? FontWeight.w700 : FontWeight.w500,
                    color: isCurrent ? AuraTheme.textPrimary : AuraTheme.textSecondary,
                  ),
                ),
                if (index < steps.length - 1) ...[
                  const SizedBox(width: 12),
                  Container(
                    width: 24,
                    height: 1,
                    color: isPassed ? AuraTheme.healthy.withValues(alpha: 0.5) : AuraTheme.border,
                  ),
                  const SizedBox(width: 12),
                ],
              ],
            );
          }),
        ),
      ),
    );
  }

  Widget _buildStepContent(AuraStateProvider state) {
    switch (_currentStep) {
      case 0:
        return _buildWelcomeStep();
      case 1:
        return _buildSessionStep(state);
      case 2:
        return _buildPrivacyPromiseStep();
      case 3:
        return _buildCapabilityCenterStep(state);
      case 4:
        return _buildReadinessStep(state);
      default:
        return _buildWelcomeStep();
    }
  }

  // -------------------------------------------------------------
  // STEP 0: WELCOME & PILLARS
  // -------------------------------------------------------------
  Widget _buildWelcomeStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Container(
          width: 68,
          height: 68,
          decoration: BoxDecoration(
            color: AuraTheme.primary.withValues(alpha: 0.15),
            shape: BoxShape.circle,
            border: Border.all(color: AuraTheme.primaryLight.withValues(alpha: 0.5), width: 1.5),
          ),
          child: const Icon(Icons.shield_rounded, color: AuraTheme.primaryLight, size: 38),
        ),
        const SizedBox(height: 20),
        const Text(
          'AURA PRIVACY GUARDIAN',
          style: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w900,
            letterSpacing: 2.2,
            color: AuraTheme.textPrimary,
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'Security and privacy intelligence for your Windows PC.',
          style: TextStyle(
            fontSize: 14,
            color: AuraTheme.textSecondary,
            fontWeight: FontWeight.w400,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 32),

        // Three Core Pillars
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: _buildPillarCard(
                icon: Icons.shield_outlined,
                title: 'PROTECT',
                subtitle: "Understand your system's security posture and real-time defense integrity.",
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _buildPillarCard(
                icon: Icons.psychology_outlined,
                title: 'UNDERSTAND',
                subtitle: 'Correlate processes, network activity, privacy signals and machine learning behaviour.',
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _buildPillarCard(
                icon: Icons.tune_rounded,
                title: 'RESPOND',
                subtitle: 'Investigate findings, isolate anomalies, and take safe, fully-audited actions.',
              ),
            ),
          ],
        ),

        const SizedBox(height: 36),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            OutlinedButton(
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                side: const BorderSide(color: AuraTheme.border),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              onPressed: _showPrivacyPrinciplesDialog,
              child: const Text(
                'HOW AURA PROTECTS YOUR PRIVACY',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 0.8),
              ),
            ),
            const SizedBox(width: 16),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AuraTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              onPressed: _nextStep,
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'GET STARTED',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, letterSpacing: 1.0),
                  ),
                  SizedBox(width: 8),
                  Icon(Icons.arrow_forward_rounded, size: 16),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildPillarCard({required IconData icon, required String title, required String subtitle}) {
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
          Icon(icon, color: AuraTheme.primaryLight, size: 28),
          const SizedBox(height: 14),
          Text(
            title,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.2,
              color: AuraTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: const TextStyle(
              fontSize: 12,
              height: 1.4,
              color: AuraTheme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // STEP 1: LOCAL SECURE SESSION
  // -------------------------------------------------------------
  Widget _buildSessionStep(AuraStateProvider state) {
    String sessionStatus = 'READY';
    Color statusColor = AuraTheme.primaryLight;
    IconData statusIcon = Icons.lock_outline_rounded;

    if (_isConnecting) {
      sessionStatus = 'CONNECTING & AUTHENTICATING...';
      statusColor = AuraTheme.warning;
      statusIcon = Icons.sync_rounded;
    } else if (_sessionConnected || state.isAuthenticated) {
      sessionStatus = 'CONNECTED & READY';
      statusColor = AuraTheme.healthy;
      statusIcon = Icons.check_circle_outline_rounded;
    } else if (_connectError != null) {
      sessionStatus = 'CONNECTION FAILED';
      statusColor = AuraTheme.critical;
      statusIcon = Icons.error_outline_rounded;
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Icon(statusIcon, color: statusColor, size: 44),
        const SizedBox(height: 16),
        const Text(
          'Local Secure Session',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AuraTheme.textPrimary),
        ),
        const SizedBox(height: 8),
        const Text(
          'AURA communicates strictly over local device loopback (127.0.0.1).\nAll security intelligence and telemetry remain completely local to your Windows PC.',
          style: TextStyle(fontSize: 13, color: AuraTheme.textSecondary, height: 1.4),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),

        // Session status pill
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: statusColor.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: statusColor.withValues(alpha: 0.35)),
          ),
          child: Text(
            sessionStatus,
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: statusColor, letterSpacing: 0.8),
          ),
        ),
        const SizedBox(height: 24),

        if (_connectError != null) ...[
          Container(
            padding: const EdgeInsets.all(14),
            margin: const EdgeInsets.only(bottom: 20),
            constraints: const BoxConstraints(maxWidth: 520),
            decoration: BoxDecoration(
              color: AuraTheme.critical.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AuraTheme.critical.withValues(alpha: 0.3)),
            ),
            child: Row(
              children: [
                const Icon(Icons.warning_amber_rounded, color: AuraTheme.critical, size: 20),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    _connectError!,
                    style: const TextStyle(fontSize: 12, color: AuraTheme.critical),
                  ),
                ),
              ],
            ),
          ),
        ],

        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (_connectError != null)
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                  side: const BorderSide(color: AuraTheme.border),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: _isConnecting ? null : () => _connectAgent(state),
                icon: const Icon(Icons.refresh_rounded, size: 16),
                label: const Text('RETRY CONNECTION', style: TextStyle(fontWeight: FontWeight.w700)),
              )
            else
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AuraTheme.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: _isConnecting
                    ? null
                    : () {
                        if (state.isAuthenticated) {
                          _nextStep();
                        } else {
                          _connectAgent(state);
                        }
                      },
                icon: _isConnecting
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.arrow_forward_rounded, size: 16),
                label: Text(
                  state.isAuthenticated ? 'CONTINUE SECURELY' : 'CONNECT LOCAL SESSION',
                  style: const TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.8),
                ),
              ),
          ],
        ),

        const SizedBox(height: 20),
        TextButton(
          onPressed: _prevStep,
          child: const Text('Back to Welcome', style: TextStyle(color: AuraTheme.textSecondary, fontSize: 12)),
        ),
      ],
    );
  }

  // -------------------------------------------------------------
  // STEP 2: PRIVACY PROMISE
  // -------------------------------------------------------------
  Widget _buildPrivacyPromiseStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.verified_user_rounded, color: AuraTheme.healthy, size: 24),
            const SizedBox(width: 10),
            const Text(
              'AURA Privacy Promise',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AuraTheme.textPrimary),
            ),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: AuraTheme.healthy.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AuraTheme.healthy.withValues(alpha: 0.3)),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.lock_rounded, color: AuraTheme.healthy, size: 12),
                  SizedBox(width: 4),
                  Text(
                    'TRANSPARENT BOUNDARIES',
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AuraTheme.healthy),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        const Text(
          'We believe cybersecurity tools must be completely transparent about what they inspect and what they never touch.',
          style: TextStyle(fontSize: 13, color: AuraTheme.textSecondary),
        ),
        const SizedBox(height: 24),

        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Left: What AURA Inspects
            Expanded(
              child: Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AuraTheme.surfaceElevated,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AuraTheme.primary.withValues(alpha: 0.3)),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.check_circle_outline_rounded, color: AuraTheme.primaryLight, size: 20),
                        SizedBox(width: 8),
                        Text(
                          'AURA INSPECTS:',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: AuraTheme.primaryLight, letterSpacing: 0.8),
                        ),
                      ],
                    ),
                    SizedBox(height: 14),
                    _PromiseItem('System security configuration & hardware posture'),
                    _PromiseItem('Process execution metadata & SHA-256 binary digests'),
                    _PromiseItem('Network socket flows & public IP classifications'),
                    _PromiseItem('Camera & Microphone Windows permission states'),
                    _PromiseItem('Windows Defender & Firewall matrix health'),
                    _PromiseItem('Security audit event logs & authentication failures'),
                    _PromiseItem('In-memory ML behavioural anomaly deviations'),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 16),

            // Right: What AURA Never Collects
            Expanded(
              child: Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AuraTheme.surfaceElevated,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AuraTheme.healthy.withValues(alpha: 0.3)),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.block_rounded, color: AuraTheme.healthy, size: 20),
                        SizedBox(width: 8),
                        Text(
                          'AURA NEVER COLLECTS:',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: AuraTheme.healthy, letterSpacing: 0.8),
                        ),
                      ],
                    ),
                    SizedBox(height: 14),
                    _PromiseItem('Webcam video frames or live camera streams'),
                    _PromiseItem('Microphone audio recordings or voice clips'),
                    _PromiseItem('Raw media files, photos, or personal documents'),
                    _PromiseItem('Packet payload contents or web browsing history'),
                    _PromiseItem('Personal user files, keystrokes, or screen captures'),
                    _PromiseItem('Private credentials or passwords'),
                    _PromiseItem('Zero data is transmitted to external cloud servers'),
                  ],
                ),
              ),
            ),
          ],
        ),

        const SizedBox(height: 28),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            TextButton(
              onPressed: _prevStep,
              child: const Text('Back to Session', style: TextStyle(color: AuraTheme.textSecondary, fontSize: 12)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AuraTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              onPressed: _nextStep,
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('CONTINUE TO CAPABILITY CENTER', style: TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.8)),
                  SizedBox(width: 8),
                  Icon(Icons.arrow_forward_rounded, size: 16),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }

  // -------------------------------------------------------------
  // STEP 3: CAPABILITY CENTER
  // -------------------------------------------------------------
  Widget _buildCapabilityCenterStep(AuraStateProvider state) {
    final capabilities = [
      _Capability(
        title: 'Camera Sentinel',
        icon: Icons.videocam_rounded,
        checks: 'Hardware device presence, driver info, Windows privacy permissions, active usage.',
        whyNeeded: 'Alerts you instantly if an unauthorized background app activates your camera.',
        doesNotCollect: 'Never captures, records, or stores webcam video frames.',
        status: state.privacySummary?.camera.isActive == true ? 'ACTIVE SENSING' : 'READY',
      ),
      _Capability(
        title: 'Microphone Sentinel',
        icon: Icons.mic_rounded,
        checks: 'Audio endpoint devices, driver info, Windows privacy permissions, active audio streams.',
        whyNeeded: 'Detects stealth microphone eavesdropping and background audio capture attempts.',
        doesNotCollect: 'Never records, processes, or stores microphone audio clips.',
        status: state.privacySummary?.microphone.isActive == true ? 'ACTIVE SENSING' : 'READY',
      ),
      _Capability(
        title: 'Process Intelligence',
        icon: Icons.account_tree_rounded,
        checks: 'Active processes, parent-child trees, SHA-256 binary hashes, elevation levels.',
        whyNeeded: 'Identifies unverified executables, privilege escalations, and stealth background tasks.',
        doesNotCollect: 'Never dumps process memory contents or private file handles.',
        status: 'ACTIVE',
      ),
      _Capability(
        title: 'Network Intelligence',
        icon: Icons.hub_rounded,
        checks: 'Active socket connections, listening ports, remote IPs, public/private classification.',
        whyNeeded: 'Detects unusual outbound beacons, unrecognized listeners, and data exfiltration patterns.',
        doesNotCollect: 'Never inspects, captures, or stores packet payload contents or web browsing history.',
        status: 'ACTIVE',
      ),
      _Capability(
        title: 'Windows Security Posture',
        icon: Icons.security_rounded,
        checks: 'Windows Defender antivirus state, Firewall profile status, TPM 2.0, Secure Boot, UAC.',
        whyNeeded: 'Ensures core Windows platform security safeguards remain enabled and uncompromised.',
        doesNotCollect: 'Never alters or disables any of your Windows security settings.',
        status: 'PROTECTED',
      ),
      _Capability(
        title: 'Event Intelligence',
        icon: Icons.history_rounded,
        checks: 'Windows Security event log entries, logon failures, credential access attempts.',
        whyNeeded: 'Provides forensic context when investigating security incidents.',
        doesNotCollect: 'Never modifies, deletes, or tampers with Windows event logs.',
        status: 'MONITORING',
      ),
      _Capability(
        title: 'Behavioural AI Ensemble',
        icon: Icons.psychology_rounded,
        checks: 'Dual-model Isolation Forest and Local Outlier Factor (LOF) anomaly envelope.',
        whyNeeded: 'Distinguishes nominal computer usage from stealth malicious behavior.',
        doesNotCollect: 'Zero external training or telemetry leakage outside your PC.',
        status: 'INITIALIZED',
      ),
      _Capability(
        title: 'Local Security Storage',
        icon: Icons.storage_rounded,
        checks: 'Encrypted local SQLite database with Write-Ahead Logging (WAL).',
        whyNeeded: 'Stores historical telemetry and audit trails on this machine for offline investigation.',
        doesNotCollect: 'Never transmits data to external servers or cloud services.',
        status: 'LOCAL WAL',
      ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.tune_rounded, color: AuraTheme.primaryLight, size: 24),
            const SizedBox(width: 10),
            const Text(
              'AURA Capability Center',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AuraTheme.textPrimary),
            ),
            const Spacer(),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                side: const BorderSide(color: AuraTheme.border),
              ),
              onPressed: () => state.openShortcut('CAMERA'),
              icon: const Icon(Icons.settings_rounded, size: 14),
              label: const Text('OPEN WINDOWS SETTINGS', style: TextStyle(fontSize: 11)),
            ),
          ],
        ),
        const SizedBox(height: 8),
        const Text(
          'Review the 8 security capabilities active on your PC. Each capability operates within strict boundaries.',
          style: TextStyle(fontSize: 13, color: AuraTheme.textSecondary),
        ),
        const SizedBox(height: 20),

        // Grid of 8 Capabilities
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            childAspectRatio: 2.1,
            crossAxisSpacing: 16,
            mainAxisSpacing: 16,
          ),
          itemCount: capabilities.length,
          itemBuilder: (context, i) {
            final cap = capabilities[i];
            return Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AuraTheme.surfaceElevated,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AuraTheme.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(cap.icon, color: AuraTheme.primaryLight, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          cap.title,
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: AuraTheme.primaryLight.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          cap.status,
                          style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: AuraTheme.primaryLight),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Checks: ${cap.checks}',
                    style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.block_rounded, size: 11, color: AuraTheme.healthy),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            cap.doesNotCollect,
                            style: const TextStyle(fontSize: 10, color: AuraTheme.healthy, fontWeight: FontWeight.w500),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        ),

        const SizedBox(height: 28),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            TextButton(
              onPressed: _prevStep,
              child: const Text('Back to Promise', style: TextStyle(color: AuraTheme.textSecondary, fontSize: 12)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AuraTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              onPressed: _nextStep,
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('CONTINUE TO READINESS CHECK', style: TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.8)),
                  SizedBox(width: 8),
                  Icon(Icons.arrow_forward_rounded, size: 16),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }

  // -------------------------------------------------------------
  // STEP 4: SYSTEM READINESS CHECK
  // -------------------------------------------------------------
  Widget _buildReadinessStep(AuraStateProvider state) {
    final checks = [
      _ReadinessItem(
        title: 'Local Security Engine API',
        detail: 'Connected via authenticated session to local loopback (127.0.0.1:8787).',
        isOk: state.isAuthenticated,
      ),
      _ReadinessItem(
        title: 'Windows Security Posture Collectors',
        detail: 'Windows Defender antivirus, Firewall matrix, and TPM 2.0 sensors active.',
        isOk: state.posture != null,
      ),
      _ReadinessItem(
        title: 'Camera Device Sentinel',
        detail: 'Windows privacy registry hooks and device inventory initialized.',
        isOk: state.privacySummary != null,
      ),
      _ReadinessItem(
        title: 'Microphone Device Sentinel',
        detail: 'Audio endpoint session monitor and driver metadata collectors verified.',
        isOk: state.privacySummary != null,
      ),
      _ReadinessItem(
        title: 'Process Telemetry Pipeline',
        detail: 'Process tree profiler and SHA-256 Authenticode hasher online.',
        isOk: state.telemetry != null,
      ),
      _ReadinessItem(
        title: 'Network Telemetry Pipeline',
        detail: 'Socket flow listeners and public/private IP classification engine online.',
        isOk: state.network != null,
      ),
      _ReadinessItem(
        title: 'Persistence Analysis Engine',
        detail: 'Registry auto-start and Windows service inspect channels verified.',
        isOk: true,
      ),
      _ReadinessItem(
        title: 'AI Anomaly Detection Ensemble',
        detail: 'Dual-model Isolation Forest and Local Outlier Factor (LOF) loaded.',
        isOk: true,
      ),
      _ReadinessItem(
        title: 'Windows Event Log Intelligence',
        detail: 'Security audit channel listener active with privilege escalation rules.',
        isOk: true,
      ),
      _ReadinessItem(
        title: 'Local SQLite Security Storage',
        detail: 'Write-Ahead Logging (WAL) database active with automatic cryptographic verification.',
        isOk: true,
      ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        const Icon(Icons.check_circle_outline_rounded, color: AuraTheme.healthy, size: 44),
        const SizedBox(height: 16),
        const Text(
          'System Readiness Check',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AuraTheme.textPrimary),
        ),
        const SizedBox(height: 8),
        const Text(
          'All 10 local AURA security subsystems are online, verified, and ready.',
          style: TextStyle(fontSize: 13, color: AuraTheme.textSecondary),
        ),
        const SizedBox(height: 20),

        // Readiness List
        Container(
          constraints: const BoxConstraints(maxWidth: 680),
          decoration: BoxDecoration(
            color: AuraTheme.surfaceElevated,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AuraTheme.borderSubtle),
          ),
          child: ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: checks.length,
            separatorBuilder: (_, index) => const Divider(height: 1, color: AuraTheme.borderSubtle),
            itemBuilder: (context, i) {
              final c = checks[i];
              return ListTile(
                dense: true,
                leading: Icon(
                  c.isOk ? Icons.check_circle_rounded : Icons.pending_rounded,
                  color: c.isOk ? AuraTheme.healthy : AuraTheme.warning,
                  size: 18,
                ),
                title: Text(
                  c.title,
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
                ),
                subtitle: Text(
                  c.detail,
                  style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary),
                ),
              );
            },
          ),
        ),

        const SizedBox(height: 28),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: AuraTheme.healthy,
            foregroundColor: Colors.black,
            padding: const EdgeInsets.symmetric(horizontal: 36, vertical: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
          onPressed: widget.onFinish,
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.space_dashboard_rounded, size: 18, color: Colors.black),
              SizedBox(width: 8),
              Text(
                'ENTER AURA COMMAND CENTER',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, letterSpacing: 1.0),
              ),
            ],
          ),
        ),
      ],
    );
  }

  void _showPrivacyPrinciplesDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AuraTheme.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: const BorderSide(color: AuraTheme.border)),
        title: const Row(
          children: [
            Icon(Icons.privacy_tip_outlined, color: AuraTheme.primaryLight, size: 22),
            SizedBox(width: 10),
            Text('AURA Privacy Commitment', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
          ],
        ),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '1. Local Processing Only',
                style: TextStyle(fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
              ),
              SizedBox(height: 4),
              Text(
                'All machine learning evaluation, process DNA extraction, and telemetry correlation run entirely on your PC CPU/memory.',
                style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
              ),
              SizedBox(height: 12),
              Text(
                '2. Zero Media Capture Guarantee',
                style: TextStyle(fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
              ),
              SizedBox(height: 4),
              Text(
                'AURA inspects Windows privacy APIs for active camera/mic sessions. It has zero capability to record audio or save webcam frames.',
                style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
              ),
              SizedBox(height: 12),
              Text(
                '3. No Payload Sniffing',
                style: TextStyle(fontWeight: FontWeight.w700, color: AuraTheme.textPrimary),
              ),
              SizedBox(height: 4),
              Text(
                'Network telemetry inspects socket endpoints and connection counts only. Packet contents and browsing traffic are never inspected.',
                style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
              ),
            ],
          ),
        ),
        actions: [
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AuraTheme.primary),
            onPressed: () => Navigator.pop(ctx),
            child: const Text('UNDERSTOOD', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }
}

class _Capability {
  final String title;
  final IconData icon;
  final String checks;
  final String whyNeeded;
  final String doesNotCollect;
  final String status;

  _Capability({
    required this.title,
    required this.icon,
    required this.checks,
    required this.whyNeeded,
    required this.doesNotCollect,
    required this.status,
  });
}

class _PromiseItem extends StatelessWidget {
  final String text;

  const _PromiseItem(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('• ', style: TextStyle(color: AuraTheme.textSecondary)),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontSize: 12, color: AuraTheme.textPrimary, height: 1.3),
            ),
          ),
        ],
      ),
    );
  }
}

class _ReadinessItem {
  final String title;
  final String detail;
  final bool isOk;

  _ReadinessItem({
    required this.title,
    required this.detail,
    required this.isOk,
  });
}
