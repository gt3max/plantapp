import 'package:flutter/material.dart';
import 'package:plantapp/app/theme.dart';

class LibraryScreen extends StatelessWidget {
  const LibraryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Text(
        'Library',
        style: TextStyle(fontSize: AppFontSize.lg, color: AppColors.text),
      ),
    );
  }
}
