import 'package:http_parser/http_parser.dart';
import 'dart:convert';
import 'dart:io';
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

// Görsel doğrulama sonucu — backend'in VerificationResult'ına karşılık gelir.
// Bu sınıf SADECE veri taşır; ağ isteği atmaz.
class VerifyResult {
  final String status; // "Verified" | "NeedsReview" | "Rejected"
  final String reason;
  final double confidence;
  final String? detectedCategory;

  VerifyResult({
    required this.status,
    required this.reason,
    required this.confidence,
    this.detectedCategory,
  });

  factory VerifyResult.fromJson(Map<String, dynamic> json) {
    return VerifyResult(
      status: json['status']?.toString() ?? 'Rejected',
      reason: json['reason']?.toString() ?? '',
      confidence: (json['confidence'] ?? 0).toDouble(),
      detectedCategory: json['detectedCategory']?.toString(),
    );
  }
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

  // Görseli verify endpoint'ine multipart olarak gönder (POST /api/taskverification/verify)
  Future<VerifyResult> verifyTaskImage({
    required String token,
    required int taskId,
    required File imageFile,
  }) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/taskverification/verify');

    final request = http.MultipartRequest('POST', url);
    request.headers['Authorization'] = 'Bearer $token';

    // taskId'yi form alanı olarak ekle
    request.fields['taskId'] = taskId.toString();

    // Dosya uzantısına göre content-type belirle (backend bunu kontrol ediyor)
    final ext = imageFile.path.toLowerCase();
    MediaType contentType;
    if (ext.endsWith('.png')) {
      contentType = MediaType('image', 'png');
    } else if (ext.endsWith('.webp')) {
      contentType = MediaType('image', 'webp');
    } else {
      contentType = MediaType('image', 'jpeg'); // .jpg / .jpeg / varsayılan
    }

    // Fotoğrafı 'image' alanı adıyla ekle (backend [FromForm] IFormFile image bekliyor)
    request.files.add(
      await http.MultipartFile.fromPath(
        'image',
        imageFile.path,
        contentType: contentType,
      ),
    );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      return VerifyResult.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 400 || response.statusCode == 404) {
      final body = jsonDecode(response.body);
      final message =
          body['Message'] ?? body['message'] ?? 'Doğrulama başarısız.';
      throw Exception(message);
    } else {
      throw Exception('Beklenmeyen hata (kod: ${response.statusCode})');
    }
  }
}
