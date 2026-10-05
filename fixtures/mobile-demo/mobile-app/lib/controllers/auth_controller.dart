import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/auth_service.dart';
class AuthController {
  Future<void> signIn() async { await AuthService().signIn(); }
}
