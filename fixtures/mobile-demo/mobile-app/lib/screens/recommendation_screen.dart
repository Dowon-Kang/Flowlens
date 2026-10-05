import 'package:flutter/material.dart';
import '../controllers/recommendation_controller.dart';
class RecommendationScreen extends StatelessWidget {
  const RecommendationScreen({super.key});
  Widget build(BuildContext context) => ElevatedButton(
    onPressed: () => RecommendationController().load(),
    child: const Text('Preview recommendation'),
  );
}
