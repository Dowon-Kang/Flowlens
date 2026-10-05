import 'package:dio/dio.dart';
class MeasurementService {
  final dio = Dio(BaseOptions(baseUrl: 'https://example.invalid'));
  Future<List<dynamic>> load() async {
    final response = await dio.get('/api/measurements');
    return response.data;
  }
}
