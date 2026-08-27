import 'package:flutter/material.dart';
import '../core/theme/aura_theme.dart';

class AuraSidebar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onItemSelected;
  final String agentStatus;
  final String version;

  const AuraSidebar({
    super.key,
    required this.selectedIndex,
    required this.onItemSelected,
    this.agentStatus = 'ONLINE',
    this.version = 'v2.0.0 (Win64)',
  });

  static const List<NavItem> items = [
    NavItem('Home', Icons.space_dashboard_rounded),
    NavItem('Security Scan', Icons.security_rounded),
    NavItem('Threat Intelligence', Icons.psychology_rounded),
    NavItem('Privacy', Icons.videocam_rounded),
    NavItem('Processes', Icons.memory_rounded),
    NavItem('Network', Icons.hub_rounded),
    NavItem('Startup & Services', Icons.repeat_rounded),
    NavItem('Security Events', Icons.stream_rounded),
    NavItem('Incidents', Icons.emergency_rounded),
    NavItem('Timeline', Icons.timeline_rounded),
    NavItem('Reports', Icons.assessment_rounded),
    NavItem('Settings', Icons.settings_rounded),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 260,
      decoration: const BoxDecoration(
        color: AuraTheme.surface,
        border: Border(
          right: BorderSide(color: AuraTheme.border, width: 1),
        ),
      ),
      child: Column(
        children: [
          // AURA Logo & Brand Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AuraTheme.borderSubtle)),
            ),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: AuraTheme.primary.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AuraTheme.primaryLight.withValues(alpha: 0.4)),
                  ),
                  child: const Icon(Icons.shield_outlined, color: AuraTheme.primaryLight, size: 22),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'AURA',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 2.0,
                        color: AuraTheme.textPrimary,
                      ),
                    ),
                    Text(
                      'PRIVACY GUARDIAN',
                      style: TextStyle(
                        fontSize: 9,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 1.2,
                        color: AuraTheme.primaryLight.withValues(alpha: 0.8),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Nav Items List
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
              itemCount: items.length,
              itemBuilder: (context, i) {
                final item = items[i];
                final isSelected = selectedIndex == i;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(8),
                      onTap: () => onItemSelected(i),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: isSelected ? AuraTheme.primary.withValues(alpha: 0.12) : Colors.transparent,
                          borderRadius: BorderRadius.circular(8),
                          border: isSelected
                              ? Border.all(color: AuraTheme.primaryLight.withValues(alpha: 0.3))
                              : null,
                        ),
                        child: Row(
                          children: [
                            Icon(
                              item.icon,
                              size: 18,
                              color: isSelected ? AuraTheme.primaryLight : AuraTheme.textSecondary,
                            ),
                            const SizedBox(width: 12),
                            Text(
                              item.title,
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                                color: isSelected ? AuraTheme.textPrimary : AuraTheme.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
          ),

          // Bottom Status Footer
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: AuraTheme.borderSubtle)),
            ),
            child: Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: AuraTheme.healthy,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  'Agent: $agentStatus',
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AuraTheme.textSecondary),
                ),
                const Spacer(),
                Text(
                  version,
                  style: const TextStyle(fontSize: 10, color: AuraTheme.textMuted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class NavItem {
  final String title;
  final IconData icon;
  const NavItem(this.title, this.icon);
}
