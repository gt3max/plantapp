import 'package:flutter/material.dart';
import 'package:plantapp/app/theme.dart';

class FleetScreen extends StatelessWidget {
  const FleetScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.devices_outlined, size: 64, color: AppColors.textSecondary),
          const SizedBox(height: AppSpacing.lg),
          const Text(
            'Fleet',
            style: TextStyle(fontSize: AppFontSize.xl, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Device management',
            style: TextStyle(fontSize: AppFontSize.md, color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}
