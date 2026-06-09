import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

// Arama / arkadaş / istek sonucu için basit model
class UserSummary {
  final int userId;
  final String username;
  final int level;

  UserSummary({
    required this.userId,
    required this.username,
    required this.level,
  });

  factory UserSummary.fromJson(Map<String, dynamic> json) {
    // arama: id/username/level, arkadaş: userId/username/level — ikisini de karşıla
    return UserSummary(
      userId: json['userId'] ?? json['id'] ?? 0,
      username: json['username'] ?? '',
      level: json['level'] ?? 1,
    );
  }
}

// Gelen istek (requestId + gönderen bilgisi)
class FriendRequest {
  final int requestId;
  final int senderId;
  final String senderUsername;
  final int senderLevel;

  FriendRequest({
    required this.requestId,
    required this.senderId,
    required this.senderUsername,
    required this.senderLevel,
  });

  factory FriendRequest.fromJson(Map<String, dynamic> json) {
    return FriendRequest(
      requestId: json['requestId'] ?? 0,
      senderId: json['senderId'] ?? 0,
      senderUsername: json['senderUsername'] ?? '',
      senderLevel: json['senderLevel'] ?? 1,
    );
  }
}

class FriendService {
  // Kullanıcı ara (GET /api/auth/search?username=...)
  Future<List<UserSummary>> searchUsers(String token, String query) async {
    final url = Uri.parse(
      '${ApiConfig.baseUrl}/api/auth/search?username=$query',
    );
    final response = await http.get(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((j) => UserSummary.fromJson(j)).toList();
    }
    throw Exception('Arama başarısız (kod: ${response.statusCode})');
  }

  // Arkadaşlık isteği gönder (POST /api/friends/add/{friendId})
  Future<String> sendRequest(String token, int friendId) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/friends/add/$friendId');
    final response = await http.post(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      return response.body.replaceAll(
        '"',
        '',
      ); // backend düz string mesaj döner
    }
    // 400'de "zaten istek var" gibi mesaj gelir
    throw Exception(response.body.replaceAll('"', ''));
  }

  // Bana gelen bekleyen istekler (GET /api/friends/requests)
  Future<List<FriendRequest>> getPendingRequests(String token) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/friends/requests');
    final response = await http.get(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((j) => FriendRequest.fromJson(j)).toList();
    }
    throw Exception('İstekler alınamadı (kod: ${response.statusCode})');
  }

  // İsteği kabul et (POST /api/friends/accept/{requestId})
  Future<void> acceptRequest(String token, int requestId) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/friends/accept/$requestId');
    final response = await http.post(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200) {
      throw Exception('İstek kabul edilemedi.');
    }
  }

  // İsteği reddet / arkadaşı sil (DELETE /api/friends/{requestId})
  Future<void> removeOrReject(String token, int requestId) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/friends/$requestId');
    final response = await http.delete(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200) {
      throw Exception('İşlem başarısız.');
    }
  }

  // Arkadaş listesi (GET /api/friends)
  Future<List<UserSummary>> getFriends(String token) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/friends');
    final response = await http.get(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((j) => UserSummary.fromJson(j)).toList();
    }
    throw Exception('Arkadaşlar alınamadı (kod: ${response.statusCode})');
  }
}
