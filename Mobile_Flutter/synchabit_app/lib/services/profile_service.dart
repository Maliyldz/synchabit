import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

class ProfileData {
  final String username;
  final int totalXp;
  final int level;
  final int xpInCurrentLevel;
  final int xpForThisLevel; // bu seviyenin toplam boyu (ilerleme paydası)
  final int xpRemaining; // sonraki seviyeye kalan

  ProfileData({
    required this.username,
    required this.totalXp,
    required this.level,
    required this.xpInCurrentLevel,
    required this.xpForThisLevel,
    required this.xpRemaining,
  });

  factory ProfileData.fromJson(Map<String, dynamic> json) {
    return ProfileData(
      username: json['username'] ?? '',
      totalXp: json['totalXp'] ?? 0,
      level: json['level'] ?? 1,
      xpInCurrentLevel: json['xpInCurrentLevel'] ?? 0,
      xpForThisLevel: json['xpForThisLevel'] ?? 100,
      xpRemaining: json['xpRemainingNewLevel'] ?? 0,
    );
  }
}

class ProfileService {
  Future<ProfileData> fetchProfile(String token) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/auth/me');
    final response = await http.get(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      return ProfileData.fromJson(jsonDecode(response.body));
    }
    throw Exception('Profil alınamadı (kod: ${response.statusCode})');
  }
}
