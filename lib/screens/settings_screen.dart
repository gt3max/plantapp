import 'package:flutter/material.dart';
import 'package:plantapp/app/theme.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: const Center(
        child: Text(
          'Settings — coming in Step 2.1',
          style: TextStyle(fontSize: AppFontSize.md, color: AppColors.textSecondary),
        ),
      ),
    );
  }
}
