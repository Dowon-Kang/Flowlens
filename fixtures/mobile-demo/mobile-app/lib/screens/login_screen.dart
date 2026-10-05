import 'package:flutter/material.dart';
import '../controllers/auth_controller.dart';
class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});
  Widget build(BuildContext context) => ElevatedButton(
    onPressed: () => AuthController().signIn(),
    child: const Text('Sign in'),
  );
}
