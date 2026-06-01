import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../models/task.dart';

// Görev oluşturma sonucunu temsil eden sınıf.
// Başarılıysa task dolu; NLP reddederse errorMessage dolu olur.
class CreateTaskResult {
  final bool success;
  final Task? task;
  final String? errorMessage;

  CreateTaskResult.ok(this.task) : success = true, errorMessage = null;

  CreateTaskResult.fail(this.errorMessage) : success = false, task = null;
}

class TaskService {
  // Görevleri listele (GET /api/tasks)
  Future<List<Task>> fetchTasks(String token) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/tasks');
    final response = await http.get(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => Task.fromJson(json)).toList();
    } else {
      throw Exception('Görevler alınamadı (kod: ${response.statusCode})');
    }
  }

  // Görev oluştur (POST /api/tasks) — NLP doğrulaması backend'de tetiklenir
  Future<CreateTaskResult> createTask({
    required String token,
    required String taskText,
    required String category,
    required int difficultyScore,
  }) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/tasks');
    try {
      final response = await http.post(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({
          'taskText': taskText,
          'category': category,
          'difficultyScore': difficultyScore,
        }),
      );

      if (response.statusCode == 200) {
        final task = Task.fromJson(jsonDecode(response.body));
        return CreateTaskResult.ok(task);
      } else if (response.statusCode == 400) {
        // NLP reddi: backend { "Message": "..." } döndürüyor
        final body = jsonDecode(response.body);
        final message =
            body['Message'] ?? body['message'] ?? 'Görev reddedildi.';
        return CreateTaskResult.fail(message);
      } else if (response.statusCode == 401) {
        return CreateTaskResult.fail(
          'Oturum süresi dolmuş. Tekrar giriş yapın.',
        );
      } else {
        return CreateTaskResult.fail(
          'Beklenmeyen hata (kod: ${response.statusCode})',
        );
      }
    } catch (e) {
      return CreateTaskResult.fail('Sunucuya bağlanılamadı.');
    }
  }
}
