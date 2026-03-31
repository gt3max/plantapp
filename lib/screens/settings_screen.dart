import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:plantapp/app/theme.dart';
import 'package:plantapp/stores/auth_store.dart';
import 'package:plantapp/stores/settings_store.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  @override
  void initState() {
    super.initState();
    final settings = ref.read(settingsProvider);
    if (!settings.isLoaded) {
      ref.read(settingsProvider.notifier).load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final settings = ref.watch(settingsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        children: [
          // Profile
          _ProfileCard(email: auth.email),
          const SizedBox(height: AppSpacing.lg),

          // Preferences
          _SectionHeader('PREFERENCES'),
          _SettingsCard(children: [
            _ToggleRow(
              icon: Icons.notifications_outlined,
              label: 'Watering Reminders',
              value: settings.notificationsEnabled,
              onChanged: (v) =>
                  ref.read(settingsProvider.notifier).setNotificationsEnabled(v),
            ),
            const Divider(height: 1),
            _SegmentRow(
              icon: Icons.thermostat_outlined,
              label: 'Temperature',
              options: const ['celsius', 'fahrenheit'],
              labels: const ['°C', '°F'],
              value: settings.temperatureUnit,
              onChanged: (v) =>
                  ref.read(settingsProvider.notifier).setTemperatureUnit(v),
            ),
            const Divider(height: 1),
            _SegmentRow(
              icon: Icons.straighten_outlined,
              label: 'Length',
              options: const ['cm', 'in'],
              labels: const ['cm', 'in'],
              value: settings.lengthUnit,
              onChanged: (v) =>
                  ref.read(settingsProvider.notifier).setLengthUnit(v),
            ),
          ]),

          const SizedBox(height: AppSpacing.lg),

          // Subscription
          _SectionHeader('SUBSCRIPTION'),
          _SettingsCard(children: [
            _TapRow(
              icon: Icons.card_membership_outlined,
              label: 'Manage Subscription',
              trailing: Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.sm, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFFDCFCE7),
                  borderRadius: AppBorderRadius.smAll,
                ),
                child: Text(
                  'Free',
                  style: TextStyle(
                    fontSize: AppFontSize.xs,
                    fontWeight: FontWeight.w700,
                    color: AppColors.primary,
                  ),
                ),
              ),
              onTap: () => _showComingSoon(context),
            ),
          ]),

          const SizedBox(height: AppSpacing.lg),

          // About
          _SectionHeader('ABOUT'),
          _SettingsCard(children: [
            _TapRow(
              icon: Icons.info_outline,
              label: 'About PlantApp',
              trailing: Text(
                'v2.0.0',
                style: TextStyle(
                  fontSize: AppFontSize.sm,
                  color: AppColors.textSecondary,
                ),
              ),
            ),
            const Divider(height: 1),
            _TapRow(
              icon: Icons.description_outlined,
              label: 'Privacy Policy',
              onTap: () => launchUrl(Uri.parse('https://plantapp.pro/privacy')),
            ),
            const Divider(height: 1),
            _TapRow(
              icon: Icons.mail_outlined,
              label: 'Contact Support',
              onTap: () =>
                  launchUrl(Uri.parse('mailto:support@plantapp.pro')),
            ),
          ]),

          const SizedBox(height: AppSpacing.lg),

          // Account
          _SectionHeader('ACCOUNT'),
          _SettingsCard(children: [
            _TapRow(
              icon: Icons.logout,
              label: 'Log Out',
              color: AppColors.error,
              onTap: () => _confirmLogout(context),
            ),
            const Divider(height: 1),
            _TapRow(
              icon: Icons.delete_outline,
              label: 'Delete Account',
              color: AppColors.error,
              onTap: () => _confirmDelete(context),
            ),
          ]),

          const SizedBox(height: AppSpacing.xxl),

          // Footer
          Center(
            child: Text(
              'PlantApp v2.0.0\nMade with care for your plants',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: AppFontSize.xs,
                color: AppColors.textSecondary,
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.xxl),
        ],
      ),
    );
  }

  void _showComingSoon(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Coming Soon'),
        content: const Text(
            'Premium subscriptions will be available when PlantApp launches on the App Store.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text('OK')),
        ],
      ),
    );
  }

  void _confirmLogout(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Log Out'),
        content: const Text('Are you sure you want to log out?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel')),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              ref.read(authProvider.notifier).logout();
            },
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Log Out'),
          ),
        ],
      ),
    );
  }

  void _confirmDelete(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Account'),
        content: const Text(
            'This will permanently delete your account and all data. This cannot be undone.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel')),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              showDialog(
                context: context,
                builder: (ctx2) => AlertDialog(
                  title: const Text('Not Available'),
                  content: const Text(
                      'Account deletion will be available in a future update. Contact support for manual deletion.'),
                  actions: [
                    TextButton(
                        onPressed: () => Navigator.pop(ctx2),
                        child: const Text('OK')),
                  ],
                ),
              );
            },
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Delete Forever'),
          ),
        ],
      ),
    );
  }
}

// ─── Helper widgets ─────────────────────────────────────────────

class _ProfileCard extends StatelessWidget {
  const _ProfileCard({required this.email});
  final String? email;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const SizedBox(height: AppSpacing.lg),
        CircleAvatar(
          radius: 32,
          backgroundColor: AppColors.primary,
          child: Text(
            (email?.isNotEmpty == true ? email![0] : '?').toUpperCase(),
            style: const TextStyle(
              fontSize: AppFontSize.xxl,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          email ?? '',
          style: TextStyle(
            fontSize: AppFontSize.md,
            fontWeight: FontWeight.w600,
            color: AppColors.text,
          ),
        ),
        Text(
          'Free Plan',
          style: TextStyle(
            fontSize: AppFontSize.sm,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
      ],
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader(this.title);
  final String title;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(
          left: AppSpacing.xs, bottom: AppSpacing.sm),
      child: Text(
        title,
        style: TextStyle(
          fontSize: AppFontSize.xs,
          fontWeight: FontWeight.w700,
          color: AppColors.textSecondary,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: AppBorderRadius.lgAll,
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(children: children),
    );
  }
}

class _TapRow extends StatelessWidget {
  const _TapRow({
    required this.icon,
    required this.label,
    this.onTap,
    this.color,
    this.trailing,
  });
  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final Color? color;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg, vertical: AppSpacing.md),
        child: Row(
          children: [
            Icon(icon, size: 22, color: color ?? AppColors.text),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  fontSize: AppFontSize.md,
                  color: color ?? AppColors.text,
                ),
              ),
            ),
            trailing ??
                Icon(Icons.chevron_right,
                    size: 18, color: AppColors.textSecondary),
          ],
        ),
      ),
    );
  }
}

class _ToggleRow extends StatelessWidget {
  const _ToggleRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.onChanged,
  });
  final IconData icon;
  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
      child: Row(
        children: [
          Icon(icon, size: 22, color: AppColors.text),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Text(label,
                style: TextStyle(fontSize: AppFontSize.md, color: AppColors.text)),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeTrackColor: AppColors.primary,
          ),
        ],
      ),
    );
  }
}

class _SegmentRow extends StatelessWidget {
  const _SegmentRow({
    required this.icon,
    required this.label,
    required this.options,
    required this.labels,
    required this.value,
    required this.onChanged,
  });
  final IconData icon;
  final String label;
  final List<String> options;
  final List<String> labels;
  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
      child: Row(
        children: [
          Icon(icon, size: 22, color: AppColors.text),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Text(label,
                style: TextStyle(fontSize: AppFontSize.md, color: AppColors.text)),
          ),
          Container(
            decoration: BoxDecoration(
              color: const Color(0xFFF3F4F6),
              borderRadius: AppBorderRadius.smAll,
            ),
            padding: const EdgeInsets.all(2),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(options.length, (i) {
                final selected = options[i] == value;
                return GestureDetector(
                  onTap: () => onChanged(options[i]),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.md, vertical: AppSpacing.xs),
                    decoration: BoxDecoration(
                      color: selected ? AppColors.surface : Colors.transparent,
                      borderRadius: BorderRadius.circular(AppBorderRadius.sm - 1),
                      boxShadow: selected
                          ? [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.1),
                                blurRadius: 2,
                                offset: const Offset(0, 1),
                              )
                            ]
                          : null,
                    ),
                    child: Text(
                      labels[i],
                      style: TextStyle(
                        fontSize: AppFontSize.sm,
                        fontWeight: FontWeight.w600,
                        color: selected
                            ? AppColors.text
                            : AppColors.textSecondary,
                      ),
                    ),
                  ),
                );
              }),
            ),
          ),
        ],
      ),
    );
  }
}
