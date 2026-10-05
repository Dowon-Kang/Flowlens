import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/recommendation_service.dart';
class RecommendationController {
  Future<void> load() async { await RecommendationService().load(); }
}
