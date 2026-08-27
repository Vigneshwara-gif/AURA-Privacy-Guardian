import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../models/process_dna.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/severity_badge.dart';

class ProcessIntelView extends StatefulWidget {
  const ProcessIntelView({super.key});

  @override
  State<ProcessIntelView> createState() => _ProcessIntelViewState();
}

class _ProcessIntelViewState extends State<ProcessIntelView> {
  final TextEditingController _searchCtrl = TextEditingController();
  String _filterType = 'ALL'; // ALL, ELEVATED, HIGH_RISK, NETWORK_ACTIVE
  String _sortBy = 'CPU'; // CPU, MEMORY, RISK, PID, NAME
  bool _showTechnicalDetails = false;
  int _selectedTabIndex = 0; // 0: DNA Overview, 1: Network & Persistence, 2: Evidence Matrix

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final dna = state.selectedProcessDna;

    if (state.targetProcessPid != null && dna?.pid != state.targetProcessPid && !state.isLoadingDna) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        state.inspectProcessDna(state.targetProcessPid!);
      });
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header banner
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AuraTheme.primary.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                  border: Border.all(color: AuraTheme.primaryLight.withValues(alpha: 0.4)),
                ),
                child: const Icon(Icons.memory_rounded, color: AuraTheme.primaryLight, size: 24),
              ),
              const SizedBox(width: 14),
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'PROCESS INTELLIGENCE & EXECUTION DNA',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.5,
                      color: AuraTheme.textPrimary,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'Understand what is running on your PC with cryptographic identity, telemetry, and behavioral AI.',
                    style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Search & Filter Controls Bar
          AuraCard(
            title: 'Process Discovery & Lookup',
            icon: Icons.search_rounded,
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: TextField(
                        controller: _searchCtrl,
                        decoration: InputDecoration(
                          hintText: 'Search by Process Name or PID (e.g. chrome.exe, 4, 11068)...',
                          prefixIcon: const Icon(Icons.search_rounded, size: 18, color: AuraTheme.textSecondary),
                          filled: true,
                          fillColor: AuraTheme.surfaceElevated,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: const BorderSide(color: AuraTheme.border),
                          ),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        ),
                        onSubmitted: (val) {
                          final pid = int.tryParse(val.trim());
                          if (pid != null) state.inspectProcessDna(pid);
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AuraTheme.primary,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      onPressed: () {
                        final pid = int.tryParse(_searchCtrl.text.trim());
                        if (pid != null) {
                          state.inspectProcessDna(pid);
                        } else {
                          // Default inspect self
                          state.inspectProcessDna(0);
                        }
                      },
                      icon: const Icon(Icons.fingerprint_rounded, size: 16),
                      label: const Text('PROFILE PROCESS DNA', style: TextStyle(fontWeight: FontWeight.w700)),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    const Text('Filter: ', style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary, fontWeight: FontWeight.w600)),
                    _buildFilterChip('ALL', 'All Processes'),
                    _buildFilterChip('ELEVATED', 'Elevated (Admin)'),
                    _buildFilterChip('HIGH_RISK', 'High Risk'),
                    _buildFilterChip('NETWORK_ACTIVE', 'Network Active'),
                    const Spacer(),
                    const Text('Sort: ', style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary, fontWeight: FontWeight.w600)),
                    _buildSortOption('CPU', 'CPU %'),
                    _buildSortOption('MEMORY', 'Memory'),
                    _buildSortOption('RISK', 'Risk Score'),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Process DNA Profile Inspection Panel
          if (state.isLoadingDna) ...[
            Container(
              padding: const EdgeInsets.all(40),
              alignment: Alignment.center,
              child: const Column(
                children: [
                  CircularProgressIndicator(color: AuraTheme.primaryLight),
                  SizedBox(height: 16),
                  Text('Extracting deep Process DNA, SHA-256 binary hash, and socket mappings...', style: TextStyle(color: AuraTheme.textSecondary)),
                ],
              ),
            ),
          ] else if (dna != null) ...[
            _buildDnaInspectionPanel(context, state, dna),
          ] else ...[
            _buildDefaultProcessListCard(state),
          ],
        ],
      ),
    );
  }

  Widget _buildFilterChip(String key, String label) {
    final isSelected = _filterType == key;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label, style: TextStyle(fontSize: 11, fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500)),
        selected: isSelected,
        selectedColor: AuraTheme.primary.withValues(alpha: 0.2),
        backgroundColor: AuraTheme.surfaceElevated,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
        onSelected: (_) => setState(() => _filterType = key),
      ),
    );
  }

  Widget _buildSortOption(String key, String label) {
    final isSelected = _sortBy == key;
    return Padding(
      padding: const EdgeInsets.only(left: 6),
      child: InkWell(
        onTap: () => setState(() => _sortBy = key),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: isSelected ? AuraTheme.primaryLight.withValues(alpha: 0.15) : Colors.transparent,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: isSelected ? AuraTheme.primaryLight : AuraTheme.borderSubtle),
          ),
          child: Text(
            label,
            style: TextStyle(fontSize: 11, color: isSelected ? AuraTheme.primaryLight : AuraTheme.textSecondary, fontWeight: FontWeight.w600),
          ),
        ),
      ),
    );
  }

  // -------------------------------------------------------------
  // DEEP PROCESS DNA INSPECTION PANEL
  // -------------------------------------------------------------
  Widget _buildDnaInspectionPanel(BuildContext context, AuraStateProvider state, ProcessDNAProfile dna) {
    final isProtected = dna.pid == 4 || dna.identity.name.toLowerCase() == 'system' || dna.identity.name.toLowerCase() == 'csrss.exe';

    return AuraCard(
      title: 'Process DNA Profile: ${dna.identity.name} (PID ${dna.pid})',
      icon: Icons.fingerprint_rounded,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          SeverityBadge(severity: dna.security.riskLevel),
          const SizedBox(width: 12),
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: isProtected ? AuraTheme.surfaceElevated : AuraTheme.critical,
              foregroundColor: isProtected ? AuraTheme.textSecondary : Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            ),
            onPressed: () => _confirmTerminateProcess(context, state, dna, isProtected),
            icon: const Icon(Icons.dangerous_rounded, size: 14),
            label: Text(
              isProtected ? 'SYSTEM PROTECTED' : 'SAFE STOP PROCESS',
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Sub-Tab Navigation Bar
          Container(
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AuraTheme.borderSubtle)),
            ),
            child: Row(
              children: [
                _buildSubTab(0, 'Identity & Execution', Icons.badge_rounded),
                _buildSubTab(1, 'Network & Sockets (${dna.network.connectionCount})', Icons.hub_rounded),
                _buildSubTab(2, 'Persistence & Privacy', Icons.shield_outlined),
                _buildSubTab(3, 'Behavioral AI & Evidence', Icons.psychology_rounded),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Sub-Tab Content
          if (_selectedTabIndex == 0) _buildIdentityAndExecutionTab(dna),
          if (_selectedTabIndex == 1) _buildNetworkAndSocketsTab(dna, state),
          if (_selectedTabIndex == 2) _buildPersistenceAndPrivacyTab(dna, state),
          if (_selectedTabIndex == 3) _buildAiAndEvidenceTab(dna),

          const SizedBox(height: 20),
          const Divider(height: 1, color: AuraTheme.borderSubtle),
          const SizedBox(height: 12),

          // Progressive Disclosure: View Technical Details
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              TextButton.icon(
                onPressed: () => setState(() => _showTechnicalDetails = !_showTechnicalDetails),
                icon: Icon(_showTechnicalDetails ? Icons.expand_less_rounded : Icons.expand_more_rounded, size: 18),
                label: Text(
                  _showTechnicalDetails ? 'HIDE TECHNICAL RAW ATTRIBUTES' : 'VIEW TECHNICAL RAW ATTRIBUTES',
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.8),
                ),
              ),
              Text(
                'Cryptographic verification source: Win32 API • SHA-256 Authenticode',
                style: const TextStyle(fontSize: 10, color: AuraTheme.textMuted),
              ),
            ],
          ),

          if (_showTechnicalDetails) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AuraTheme.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildTechnicalItem('Command Line Arguments', dna.identity.cmdline ?? 'None passed'),
                  _buildTechnicalItem('Binary SHA-256 Hash', dna.identity.sha256Hash ?? 'Not accessible'),
                  _buildTechnicalItem('Parent Process Identity', '${dna.identity.parentName ?? "None"} (PPID ${dna.identity.parentPid})'),
                  _buildTechnicalItem('Execution Handles Count', '${dna.execution.numHandles} system handles'),
                  _buildTechnicalItem('Anomaly Model Attribution', 'Isolation Forest Score: ${dna.security.riskScore} • LOF Attribution nominal'),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSubTab(int index, String label, IconData icon) {
    final isSelected = _selectedTabIndex == index;
    return InkWell(
      onTap: () => setState(() => _selectedTabIndex = index),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
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
            Icon(icon, size: 14, color: isSelected ? AuraTheme.primaryLight : AuraTheme.textSecondary),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                color: isSelected ? AuraTheme.textPrimary : AuraTheme.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // SubTab 0: Identity & Execution
  Widget _buildIdentityAndExecutionTab(ProcessDNAProfile dna) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildDnaField('Executable Path', dna.identity.exePath ?? 'C:\\Windows\\System32\\...'),
                  _buildDnaField('User Account Context', dna.identity.username ?? 'LOCAL SYSTEM / User'),
                  _buildDnaField('Elevation Status', dna.identity.isElevated ? 'ADMINISTRATIVE / ELEVATED TOKEN' : 'STANDARD TOKEN'),
                  _buildDnaField('Parent Process', '${dna.identity.parentName ?? "services.exe"} (PID ${dna.identity.parentPid})'),
                ],
              ),
            ),
            const SizedBox(width: 20),
            Expanded(
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AuraTheme.surfaceElevated,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AuraTheme.borderSubtle),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Execution Telemetry', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.primaryLight)),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        _buildStatBox(label: 'CPU Usage', value: '${dna.execution.cpuPercent.toStringAsFixed(1)}%'),
                        const SizedBox(width: 8),
                        _buildStatBox(label: 'Memory RSS', value: '${dna.execution.memoryMb.toStringAsFixed(1)} MB'),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        _buildStatBox(label: 'Threads', value: '${dna.execution.numThreads}'),
                        const SizedBox(width: 8),
                        _buildStatBox(label: 'Handles', value: '${dna.execution.numHandles}'),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  // SubTab 1: Network & Sockets
  Widget _buildNetworkAndSocketsTab(ProcessDNAProfile dna, AuraStateProvider state) {
    final conns = dna.network.connections;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text('Active Sockets: ${dna.network.connectionCount}', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
            const Spacer(),
            Text('Remote Public IPs: ${dna.network.remoteIps.length}', style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
          ],
        ),
        const SizedBox(height: 12),
        if (conns.isEmpty)
          Container(
            padding: const EdgeInsets.all(20),
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AuraTheme.surfaceElevated,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Text('Zero active network socket descriptors open for this process.', style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary)),
          )
        else
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: conns.length,
            separatorBuilder: (_, index) => const Divider(height: 1, color: AuraTheme.borderSubtle),
            itemBuilder: (context, i) {
              final c = conns[i];
              return ListTile(
                dense: true,
                leading: const Icon(Icons.link_rounded, size: 16, color: AuraTheme.primaryLight),
                title: Text('${c.localAddress}:${c.localPort} ➔ ${c.remoteAddress}:${c.remotePort}', style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
                subtitle: Text('Status: ${c.status} • Protocol: ${c.protocol}', style: const TextStyle(fontSize: 10, color: AuraTheme.textSecondary)),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SeverityBadge(severity: c.isPublic ? 'MEDIUM' : 'NORMAL'),
                    const SizedBox(width: 8),
                    IconButton(
                      icon: const Icon(Icons.arrow_forward_rounded, size: 14, color: AuraTheme.primaryLight),
                      tooltip: 'View in Network Intelligence',
                      onPressed: () => state.navigateTo(5, targetIp: c.remoteAddress),
                    ),
                  ],
                ),
              );
            },
          ),
      ],
    );
  }

  // SubTab 2: Persistence & Privacy
  Widget _buildPersistenceAndPrivacyTab(ProcessDNAProfile dna, AuraStateProvider state) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        InkWell(
          onTap: () => state.navigateTo(6),
          child: _buildDnaField('Auto-Start Location', '${dna.persistence.startupEntry ?? "None (Not configured in startup registry)"} (Tap to view Persistence)'),
        ),
        InkWell(
          onTap: () => state.navigateTo(6),
          child: _buildDnaField('Windows Service Hook', '${dna.persistence.serviceName ?? "None (Standalone user process)"} (Tap to view Services)'),
        ),
        InkWell(
          onTap: () => state.navigateTo(6),
          child: _buildDnaField('Scheduled Task Link', dna.persistence.scheduledTaskName ?? 'None (No automated scheduled tasks)'),
        ),
        InkWell(
          onTap: () => state.navigateTo(3),
          child: _buildDnaField('Camera Sentinel State', '${dna.privacy.hasCameraAccess ? "CAMERA PERMITTED / ACTIVE" : "NO CAMERA ACCESS DETECTED"} (Tap to view Privacy Sentinel)'),
        ),
        InkWell(
          onTap: () => state.navigateTo(3),
          child: _buildDnaField('Microphone Sentinel State', '${dna.privacy.hasMicrophoneAccess ? "MICROPHONE PERMITTED" : "NO MICROPHONE ACCESS DETECTED"} (Tap to view Privacy Sentinel)'),
        ),
      ],
    );
  }

  // SubTab 3: AI & Evidence
  Widget _buildAiAndEvidenceTab(ProcessDNAProfile dna) {
    final evidence = dna.evidence;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text('Composite Risk Score: ${dna.security.riskScore}/100', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: AuraTheme.textPrimary)),
            const SizedBox(width: 12),
            SeverityBadge(severity: dna.security.riskLevel),
          ],
        ),
        const SizedBox(height: 12),
        _buildEvidenceSection('Observed Facts', evidence.observed, AuraTheme.healthy, Icons.visibility_rounded),
        const SizedBox(height: 8),
        _buildEvidenceSection('Inferred Patterns', evidence.inferred, AuraTheme.primaryLight, Icons.psychology_rounded),
        const SizedBox(height: 8),
        _buildEvidenceSection('Suspected Indicators', evidence.suspected, AuraTheme.warning, Icons.warning_amber_rounded),
      ],
    );
  }

  Widget _buildEvidenceSection(String title, List<String> items, Color color, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AuraTheme.surfaceElevated,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AuraTheme.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 6),
              Text(title, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: color)),
              const SizedBox(width: 8),
              Text('(${items.length})', style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
            ],
          ),
          if (items.isNotEmpty) ...[
            const SizedBox(height: 6),
            ...items.map((it) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('• ', style: TextStyle(color: AuraTheme.textSecondary)),
                      Expanded(child: Text(it, style: const TextStyle(fontSize: 11, color: AuraTheme.textPrimary))),
                    ],
                  ),
                )),
          ],
        ],
      ),
    );
  }

  Widget _buildDnaField(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary, fontWeight: FontWeight.w600)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontSize: 13, color: AuraTheme.textPrimary, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  Widget _buildTechnicalItem(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 180,
            child: Text(label, style: const TextStyle(fontSize: 11, color: AuraTheme.primaryLight, fontWeight: FontWeight.w600)),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary, fontFamily: 'monospace')),
          ),
        ],
      ),
    );
  }

  Widget _buildStatBox({required String label, required String value}) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.3),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 10, color: AuraTheme.textSecondary)),
            const SizedBox(height: 4),
            Text(value, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: AuraTheme.textPrimary)),
          ],
        ),
      ),
    );
  }

  // Default Process List
  Widget _buildDefaultProcessListCard(AuraStateProvider state) {
    final fallbackPids = [
      {'name': 'aura_desktop.exe', 'pid': 11068, 'cpu': '0.4%', 'mem': '68 MB', 'risk': 'LOW'},
      {'name': 'python.exe', 'pid': 31756, 'cpu': '0.8%', 'mem': '94 MB', 'risk': 'LOW'},
      {'name': 'explorer.exe', 'pid': 4812, 'cpu': '0.1%', 'mem': '112 MB', 'risk': 'LOW'},
      {'name': 'svchost.exe', 'pid': 1420, 'cpu': '0.0%', 'mem': '24 MB', 'risk': 'LOW'},
      {'name': 'System', 'pid': 4, 'cpu': '0.0%', 'mem': '12 MB', 'risk': 'PROTECTED'},
    ];

    return AuraCard(
      title: 'Active Monitored Windows Processes',
      icon: Icons.list_alt_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Select any process below or enter a PID above to extract its complete Process DNA profile.',
            style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary),
          ),
          const SizedBox(height: 16),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: fallbackPids.length,
            separatorBuilder: (_, index) => const Divider(height: 1, color: AuraTheme.borderSubtle),
            itemBuilder: (context, i) {
              final p = fallbackPids[i];
              return ListTile(
                leading: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AuraTheme.surfaceElevated,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Icon(Icons.memory_rounded, size: 16, color: AuraTheme.primaryLight),
                ),
                title: Text(p['name'] as String, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
                subtitle: Text('PID ${p['pid']} • CPU ${p['cpu']} • Memory ${p['mem']}', style: const TextStyle(fontSize: 11, color: AuraTheme.textSecondary)),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SeverityBadge(severity: p['risk'] as String),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AuraTheme.primary,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      ),
                      onPressed: () => state.inspectProcessDna(p['pid'] as int),
                      child: const Text('INSPECT DNA', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700)),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  void _confirmTerminateProcess(BuildContext context, AuraStateProvider state, ProcessDNAProfile dna, bool isProtected) {
    if (isProtected) {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: AuraTheme.surface,
          title: const Text('System Protected Process', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AuraTheme.critical)),
          content: Text('Cannot terminate ${dna.identity.name} (PID ${dna.pid}). AURA safeguards critical Windows kernel/system processes to prevent Blue Screens (BSOD) or OS instability.'),
          actions: [
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: AuraTheme.primary),
              onPressed: () => Navigator.pop(ctx),
              child: const Text('OK', style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      );
      return;
    }

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AuraTheme.surface,
        title: Text('Stop Process ${dna.identity.name}?', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
        content: Text('Are you sure you want to terminate ${dna.identity.name} (PID ${dna.pid})?\n\nAURA will log this action to the local cryptographic audit ledger.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('CANCEL', style: TextStyle(color: AuraTheme.textSecondary)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AuraTheme.critical),
            onPressed: () async {
              Navigator.pop(ctx);
              final ok = await state.terminateProcess(dna.pid);
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    backgroundColor: ok ? AuraTheme.healthy : AuraTheme.critical,
                    content: Text(ok ? 'Successfully stopped process ${dna.identity.name} (PID ${dna.pid}).' : 'Failed to terminate process.'),
                  ),
                );
              }
            },
            child: const Text('TERMINATE PROCESS', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }
}
