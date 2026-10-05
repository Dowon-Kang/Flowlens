import 'package:dio/dio.dart';
class AuthService {
  final dio = Dio(BaseOptions(baseUrl: 'https://example.invalid'));
  Future<void> signIn() async {
    await dio.post('/api/auth/login', data: {'email': 'demo@example.invalid'});
  }
}
