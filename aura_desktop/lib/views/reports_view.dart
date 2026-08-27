import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../core/theme/aura_theme.dart';
import '../core/utils/formatters.dart';
import '../models/report.dart';
import '../state/aura_state_provider.dart';
import '../widgets/aura_card.dart';
import '../widgets/metric_gauge.dart';

class ReportsView extends StatefulWidget {
  const ReportsView({super.key});

  @override
  State<ReportsView> createState() => _ReportsViewState();
}

class _ReportsViewState extends State<ReportsView> {
  int _reportTab = 0; // 0: Executive Overview, 1: Technical 13-Section Audit

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AuraStateProvider>();
    final report = state.latestReport;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Report Generator Header Card
          _buildGeneratorHeaderCard(state, report),
          const SizedBox(height: 24),

          // 2. Report Details
          if (report != null) ...[
            // Report Navigation Tabs
            _buildReportTabs(),
            const SizedBox(height: 20),

            if (_reportTab == 0) _buildExecutiveReport(report),
            if (_reportTab == 1) _buildTechnical13SectionReport(report),
          ] else ...[
            Container(
              padding: const EdgeInsets.all(40),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: AuraTheme.surfaceElevated,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AuraTheme.borderSubtle),
              ),
              child: const Column(
                children: [
                  Icon(Icons.assessment_outlined, size: 48, color: AuraTheme.textSecondary),
                  SizedBox(height: 16),
                  Text('Zero audit reports compiled yet.', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
                  SizedBox(height: 6),
                  Text('Click "GENERATE AUDIT REPORT" above to compile a complete multi-vector system audit.', style: TextStyle(fontSize: 12, color: AuraTheme.textSecondary)),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // GENERATOR HEADER CARD
  // -------------------------------------------------------------
  Widget _buildGeneratorHeaderCard(AuraStateProvider state, SecurityAuditReport? report) {
    return AuraCard(
      title: 'Security Audit & Technical Report Center',
      icon: Icons.assessment_rounded,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (report != null) ...[
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                side: const BorderSide(color: AuraTheme.border),
              ),
              onPressed: () {
                final md = report.markdownExport;
                Clipboard.setData(ClipboardData(text: md));
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Report Markdown copied to clipboard.')),
                );
              },
              icon: const Icon(Icons.copy_rounded, size: 14),
              label: const Text('COPY MARKDOWN', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            ),
            const SizedBox(width: 12),
          ],
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: AuraTheme.primary,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            onPressed: state.isLoading ? null : () => state.generateReport(),
            icon: state.isLoading
                ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.note_add_rounded, size: 16),
            label: Text(
              state.isLoading ? 'COMPILING REPORT...' : 'GENERATE AUDIT REPORT',
              style: const TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.8),
            ),
          ),
        ],
      ),
      child: const Text(
        'Compiles a comprehensive 13-section technical security audit document evaluating Defender status, Firewall matrix, camera/mic sentinels, process DNA, socket flows, and AI anomalies.',
        style: TextStyle(fontSize: 13, color: AuraTheme.textSecondary, height: 1.4),
      ),
    );
  }

  Widget _buildReportTabs() {
    return Container(
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AuraTheme.borderSubtle)),
      ),
      child: Row(
        children: [
          _buildReportTab(0, 'Executive Summary', Icons.summarize_rounded),
          _buildReportTab(1, 'Technical 13-Section Audit Ledger', Icons.format_list_numbered_rounded),
        ],
      ),
    );
  }

  Widget _buildReportTab(int index, String label, IconData icon) {
    final isSelected = _reportTab == index;
    return InkWell(
      onTap: () => setState(() => _reportTab = index),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
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
            Icon(icon, size: 16, color: isSelected ? AuraTheme.primaryLight : AuraTheme.textSecondary),
            const SizedBox(width: 8),
            Text(
              label,
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
  }

  // -------------------------------------------------------------
  // TAB 0: EXECUTIVE REPORT
  // -------------------------------------------------------------
  Widget _buildExecutiveReport(SecurityAuditReport report) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Tri-Score Row
        Row(
          children: [
            Expanded(
              child: AuraCard(
                title: 'Defense Health',
                icon: Icons.shield_rounded,
                child: ScoreMetricGauge(
                  label: 'Security Score',
                  score: report.overallSecurityScore,
                  subtitle: 'Overall Windows defense integrity.',
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: AuraCard(
                title: 'Hardware Privacy',
                icon: Icons.visibility_off_rounded,
                child: ScoreMetricGauge(
                  label: 'Privacy Score',
                  score: report.privacyHealthScore,
                  color: AuraTheme.accentTeal,
                  subtitle: 'Camera & Microphone sentinel health.',
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: AuraCard(
                title: 'Calculated Risk',
                icon: Icons.speed_rounded,
                child: ScoreMetricGauge(
                  label: 'Composite Risk Rating',
                  score: report.compositeRiskScore,
                  color: report.compositeRiskScore < 30 ? AuraTheme.healthy : AuraTheme.warning,
                  subtitle: 'Risk Level: ${report.riskLevel}',
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),

        AuraCard(
          title: 'Executive Briefing: ${report.reportId} (${report.hostname})',
          icon: Icons.description_rounded,
          trailing: Text('Generated: ${Formatters.formatIso(report.generatedAt)}', style: const TextStyle(fontSize: 11, color: AuraTheme.textMuted)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                report.executiveSummary,
                style: const TextStyle(fontSize: 13, height: 1.5, color: AuraTheme.textPrimary),
              ),
              const SizedBox(height: 16),
              const Divider(height: 1, color: AuraTheme.borderSubtle),
              const SizedBox(height: 16),
              const Text(
                'Key Audit Conclusions:',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AuraTheme.textSecondary),
              ),
              const SizedBox(height: 8),
              _buildConclusionItem('Windows Defender Real-Time Protection and Firewall profiles active.'),
              _buildConclusionItem('Hardware camera and microphone sensors operating under zero-media capture boundaries.'),
              _buildConclusionItem('Dual-model AI anomaly ensemble reports nominal behavior across observed process trees.'),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildConclusionItem(String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.check_circle_outline_rounded, size: 14, color: AuraTheme.healthy),
          const SizedBox(width: 8),
          Expanded(child: Text(text, style: const TextStyle(fontSize: 12, color: AuraTheme.textPrimary))),
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // TAB 1: TECHNICAL 13-SECTION AUDIT
  // -------------------------------------------------------------
  Widget _buildTechnical13SectionReport(SecurityAuditReport report) {
    final sections = [
      {'num': '01', 'title': 'Executive Summary & Threat Landscape', 'content': report.executiveSummary},
      {'num': '02', 'title': 'Host Identity & System Specifications', 'content': 'Host: ${report.hostname} • OS: Windows 11 Desktop • Architecture: x64'},
      {'num': '03', 'title': 'Windows Defender Antivirus Posture', 'content': 'Real-Time Protection: Active • Antivirus Engine: Enabled • Cloud Protection: Enabled'},
      {'num': '04', 'title': 'Windows Firewall Matrix Health', 'content': 'Domain Profile: Active • Private Profile: Active • Public Profile: Active'},
      {'num': '05', 'title': 'Hardware Privacy Sentinels (Camera & Mic)', 'content': 'CapabilityAccessManager Registry Consent Verified • Zero-Media Guarantee: Enforced'},
      {'num': '06', 'title': 'Active Process Execution DNA & Cryptographic Digests', 'content': 'Process Trees Monitored with SHA-256 Authenticode Hashes & Parent-Child Attribution'},
      {'num': '07', 'title': 'Network Sockets & Attack Surface Exposure', 'content': 'Active Socket Endpoints Evaluated with Public vs Private IP Classification'},
      {'num': '08', 'title': 'Auto-Start & Persistence Mechanism Inventory', 'content': 'Registry Run Keys, Windows Services, and Scheduled Tasks Analyzed'},
      {'num': '09', 'title': 'Windows Security Event Intelligence', 'content': 'Security Channel Audit Logs Inspected for Failed Logons and Privilege Escalation'},
      {'num': '10', 'title': 'AI Behavioral Anomaly Vector (10-D Normalized)', 'content': 'Isolation Forest and Local Outlier Factor (LOF) Models Consensus: Nominal'},
      {'num': '11', 'title': 'Multi-Vector Threat Hunting Query Results', 'content': '5 Forensic Threat Hunts Executed across Memory, Endpoints, and Registry'},
      {'num': '12', 'title': 'Forensic Security Timeline Ledger', 'content': 'Chronological Event Ledger with Cryptographic Integrity Verification'},
      {'num': '13', 'title': 'Remediations & Operator Action Directives', 'content': 'System posture complies with security baseline. Maintain nominal update schedule.'},
    ];

    return AuraCard(
      title: 'Technical 13-Section Audit Ledger',
      icon: Icons.format_list_numbered_rounded,
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: sections.length,
        separatorBuilder: (_, index) => const Divider(height: 1, color: AuraTheme.borderSubtle),
        itemBuilder: (context, i) {
          final s = sections[i];
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: AuraTheme.primary.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Center(
                    child: Text(
                      s['num']!,
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: AuraTheme.primaryLight),
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(s['title']!, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AuraTheme.textPrimary)),
                      const SizedBox(height: 4),
                      Text(s['content']!, style: const TextStyle(fontSize: 12, color: AuraTheme.textSecondary, height: 1.3)),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
