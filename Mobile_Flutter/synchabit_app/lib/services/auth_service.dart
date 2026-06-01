import 'package:http/http.dart' as http;
import '../config/api_config.dart';

// Servisten dönen sonucu temsil eden basit sınıf.
// Başarılıysa token dolu, değilse errorMessage dolu olur.
class AuthResponse {
  final bool success;
  final String? token;
  final String? errorMessage;

  AuthResponse.ok(this.token) : success = true, errorMessage = null;

  AuthResponse.fail(this.errorMessage) : success = false, token = null;
}

class AuthService {
  Future<AuthResponse> login(String email, String password) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/auth/login');
    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: '{"email": "$email", "password": "$password"}',
      );

      if (response.statusCode == 200) {
        // Backend düz token string'i dönüyor: "eyJ...".
        // Baştaki/sondaki çift tırnağı temizliyoruz.
        final token = response.body.replaceAll('"', '');
        return AuthResponse.ok(token);
      } else {
        // BadRequest gövdesinde Türkçe hata mesajı var (örn. "Hatalı şifre.")
        return AuthResponse.fail(_cleanMessage(response.body));
      }
    } catch (e) {
      return AuthResponse.fail('Sunucuya bağlanılamadı. Backend çalışıyor mu?');
    }
  }

  Future<AuthResponse> register(
    String username,
    String email,
    String password,
  ) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/auth/register');
    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body:
            '{"username": "$username", "email": "$email", "password": "$password"}',
      );

      if (response.statusCode == 200) {
        return AuthResponse.ok(null); // register token döndürmüyor
      } else {
        return AuthResponse.fail(_cleanMessage(response.body));
      }
    } catch (e) {
      return AuthResponse.fail('Sunucuya bağlanılamadı. Backend çalışıyor mu?');
    }
  }

  String _cleanMessage(String body) {
    return body.replaceAll('"', '').trim();
  }
}
