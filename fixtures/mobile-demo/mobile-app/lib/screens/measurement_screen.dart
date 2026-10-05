import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../controllers/measurement_controller.dart';
class MeasurementScreen extends ConsumerWidget {
  const MeasurementScreen({super.key});
  Widget build(BuildContext context, WidgetRef ref) {
    return ElevatedButton(
      onPressed: () => ref.read(measurementProvider.notifier).load(),
      child: const Text('Load measurements'),
    );
  }
}
