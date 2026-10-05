import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/measurement_service.dart';
final measurementProvider = StateNotifierProvider<MeasurementController, List<dynamic>>(
  (ref) => MeasurementController(),
);
class MeasurementController extends StateNotifier<List<dynamic>> {
  MeasurementController() : super([]);
  Future<void> load() async { state = await MeasurementService().load(); }
}
