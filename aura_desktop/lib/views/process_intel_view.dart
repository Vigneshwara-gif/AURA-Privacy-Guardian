import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
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

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final dna = state.selectedProcessDna;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Process Search & DNA Lookup Card
          AuraCard(
            title: 'Process DNA & Execution Profiler',
            icon: Icons.memory_rounded,
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchCtrl,
                    decoration: InputDecoration(
                      hintText: 'Enter Process PID (e.g., ${state.telemetry != null ? 0 : ""})...',
                      filled: true,
                      fillColor: AuraTheme.surfaceElevated,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                    keyboardType: TextInputType.number,
                  ),
                ),
                const SizedBox(width: 16),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AuraTheme.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                  ),
                  onPressed: () {
                    final pid = int.tryParse(_searchCtrl.text.trim());
                    if (pid != null) {
                      state.inspectProcessDna(pid);
                    }
                  },
                  icon: const Icon(Icons.fingerprint_rounded, size: 16),
                  label: const Text('EXTRACT PROCESS DNA', style: TextStyle(fontWeight: FontWeight.w700)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Process DNA Profile Details
          if (state.isLoadingDna)
            const Center(child: CircularProgressIndicator())
          else if (dna != null) ...[
            AuraCard(
              title: 'Process DNA Profile: ${dna.identity.name} (PID ${dna.pid})',
              icon: Icons.fingerprint_rounded,
              trailing: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: AuraTheme.critical, foregroundColor: Colors.white),
                onPressed: () async {
                  final ok = await state.terminateProcess(dna.pid);
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text(ok ? 'Process PID ${dna.pid} terminated.' : 'Failed or protected process.')),
                    );
                  }
                },
                icon: const Icon(Icons.dangerous_rounded, size: 14),
                label: const Text('SAFE STOP PROCESS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Identity Matrix
                  _SectionHeader(title: 'Identity & Provenance'),
                  _DnaRow('Executable Path', dna.identity.exePath ?? 'Unknown'),
                  _DnaRow('SHA-256 Digest', dna.identity.sha256Hash ?? 'Computing or Inaccessible'),
                  _DnaRow('User Context', dna.identity.username ?? 'Standard User'),
                  _DnaRow('Elevation State', dna.identity.isElevated ? 'ELEVATED / SYSTEM' : 'STANDARD TOKEN'),
                  _DnaRow('Parent Process', '${dna.identity.parentName ?? "N/A"} (PPID ${dna.identity.parentPid})'),
                  _DnaRow('Command Line', dna.identity.cmdline ?? 'None'),
                  const SizedBox(height: 16),

                  // Execution Metrics
                  _SectionHeader(title: 'Live Execution Telemetry'),
                  Row(
                    children: [
                      _StatBox(label: 'CPU Usage', value: '${dna.execution.cpuPercent}%'),
                      const SizedBox(width: 12),
                      _StatBox(label: 'Resident RAM', value: '${dna.execution.memoryMb} MB'),
                      const SizedBox(width: 12),
                      _StatBox(label: 'Active Threads', value: '${dna.execution.numThreads}'),
                      const SizedBox(width: 12),
                      _StatBox(label: 'Handles', value: '${dna.execution.numHandles}'),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Risk & Security Analysis
                  _SectionHeader(title: 'Security & Behavioral Assessment'),
                  Row(
                    children: [
                      Text('Assessed Risk: ${dna.security.riskScore}/100',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            color: dna.security.riskScore < 25 ? AuraTheme.healthy : AuraTheme.critical,
                          )),
                      const SizedBox(width: 12),
                      SeverityBadge(severity: dna.security.riskLevel),
                    ],
                  ),
                ],
              ),
            ),
          ] else
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 32),
              child: Center(
                child: Text('Enter a Process PID above to view complete DNA, sockets, memory footprint, and risk indicators.',
                    style: TextStyle(color: AuraTheme.textSecondary)),
              ),
            ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.primaryLight)),
    );
  }
}

class _DnaRow extends StatelessWidget {
  final String label;
  final String value;
  const _DnaRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 140, child: Text(label, style: const TextStyle(fontSize: 12, color: AuraTheme.textSecondary))),
          Expanded(child: Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AuraTheme.textPrimary))),
        ],
      ),
    );
  }
}

class _StatBox extends StatelessWidget {
  final String label;
  final String value;
  const _StatBox({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AuraTheme.surfaceElevated,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: AuraTheme.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 10, color: AuraTheme.textSecondary)),
            const SizedBox(height: 4),
            Text(value, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AuraTheme.textPrimary)),
          ],
        ),
      ),
    );
  }
}
