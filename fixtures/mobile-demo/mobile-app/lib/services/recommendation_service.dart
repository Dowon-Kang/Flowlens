import 'package:dio/dio.dart';
class RecommendationService {
  final dio = Dio(BaseOptions(baseUrl: 'https://example.invalid'));
  Future<dynamic> load() async {
    return (await dio.post('/api/recommendations')).data;
  }
}
