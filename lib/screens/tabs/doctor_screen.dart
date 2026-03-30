import 'package:flutter/material.dart';
import 'package:plantapp/app/theme.dart';

class DoctorScreen extends StatelessWidget {
  const DoctorScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.medical_services_outlined, size: 64, color: AppColors.textSecondary),
          const SizedBox(height: AppSpacing.lg),
          const Text(
            'AI Doctor',
            style: TextStyle(fontSize: AppFontSize.xl, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Coming Soon',
            style: TextStyle(fontSize: AppFontSize.md, color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}
