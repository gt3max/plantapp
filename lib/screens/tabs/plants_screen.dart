import 'package:flutter/material.dart';
import 'package:plantapp/app/theme.dart';

class PlantsScreen extends StatelessWidget {
  const PlantsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Text(
        'My Plants',
        style: TextStyle(fontSize: AppFontSize.lg, color: AppColors.text),
      ),
    );
  }
}
