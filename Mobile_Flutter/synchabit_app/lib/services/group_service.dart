import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../models/group.dart';
import '../models/task.dart';
import 'task_service.dart';

class GroupService {
  // Üye olduğum grupları getir (GET /api/groups/mine)
  Future<List<Group>> fetchMyGroups(String token) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/groups/mine');
    final response = await http.get(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => Group.fromJson(json)).toList();
    } else {
      throw Exception('Gruplar alınamadı (kod: ${response.statusCode})');
    }
  }

  // Grup oluştur (POST /api/groups)
  Future<Group> createGroup({
    required String token,
    required String name,
    required String description,
  }) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/groups');
    final response = await http.post(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({'name': name, 'description': description}),
    );
    if (response.statusCode == 200) {
      // Backend oluşturulan Group'u döndürüyor ama isLeader içermez;
      // oluşturan kişi her zaman liderdir, o yüzden listeyi tazeleyince doğru gelir.
      return Group.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Grup oluşturulamadı (kod: ${response.statusCode})');
    }
  }

  // Grup üyelerini getir (GET /api/groups/{id}/members)
  Future<List<GroupMember>> fetchMembers(String token, int groupId) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/groups/$groupId/members');
    final response = await http.get(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => GroupMember.fromJson(json)).toList();
    } else {
      throw Exception('Üyeler alınamadı (kod: ${response.statusCode})');
    }
  }

  // Grup görevlerini getir (GET /api/groups/{id}/tasks)
  Future<List<Task>> fetchGroupTasks(String token, int groupId) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/groups/$groupId/tasks');
    final response = await http.get(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => Task.fromJson(json)).toList();
    } else {
      throw Exception('Grup görevleri alınamadı (kod: ${response.statusCode})');
    }
  }

  // Gruba görev ekle (POST /api/groups/{id}/task) — NLP backend'de tetiklenir
  Future<CreateTaskResult> addGroupTask({
    required String token,
    required int groupId,
    required String taskText,
    required String category,
    required int difficultyScore,
  }) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/groups/$groupId/task');
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
        final body = jsonDecode(response.body);
        final message =
            body['Message'] ?? body['message'] ?? 'Görev reddedildi.';
        return CreateTaskResult.fail(message);
      } else if (response.statusCode == 401) {
        return CreateTaskResult.fail('Bu gruba görev ekleme yetkiniz yok.');
      } else {
        return CreateTaskResult.fail(
          'Beklenmeyen hata (kod: ${response.statusCode})',
        );
      }
    } catch (e) {
      return CreateTaskResult.fail('Sunucuya bağlanılamadı.');
    }
  }

  // Arkadaşı gruba davet et (POST /api/groups/{groupId}/invite/{friendId})
  Future<String> inviteToGroup({
    required String token,
    required int groupId,
    required int friendId,
  }) async {
    final url = Uri.parse(
      '${ApiConfig.baseUrl}/api/groups/$groupId/invite/$friendId',
    );
    final response = await http.post(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      return response.body.replaceAll('"', ''); // "Davet gönderildi."
    }
    // 400: "zaten üye", "zaten davet var", "sadece arkadaş" gibi mesajlar
    throw Exception(response.body.replaceAll('"', ''));
  }

  // Bana gelen grup davetleri (GET /api/groups/invites)
  Future<List<GroupInvite>> fetchMyInvites(String token) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/groups/invites');
    final response = await http.get(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((j) => GroupInvite.fromJson(j)).toList();
    }
    throw Exception('Davetler alınamadı (kod: ${response.statusCode})');
  }

  // Daveti kabul et (POST /api/groups/invites/{inviteId}/accept)
  Future<void> acceptInvite(String token, int inviteId) async {
    final url = Uri.parse(
      '${ApiConfig.baseUrl}/api/groups/invites/$inviteId/accept',
    );
    final response = await http.post(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200) {
      throw Exception('Davet kabul edilemedi.');
    }
  }

  // Bir grubun bekleyen onayları (GET /api/groups/{id}/pending)
  Future<List<PendingApproval>> fetchPendingApprovals(
    String token,
    int groupId,
  ) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/api/groups/$groupId/pending');
    final response = await http.get(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((j) => PendingApproval.fromJson(j)).toList();
    }
    throw Exception('Onaylar alınamadı (kod: ${response.statusCode})');
  }

  // Tamamlamayı onayla (POST /api/groups/completions/{id}/approve)
  Future<void> approveCompletion(String token, int completionId) async {
    final url = Uri.parse(
      '${ApiConfig.baseUrl}/api/groups/completions/$completionId/approve',
    );
    final response = await http.post(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200) throw Exception('Onaylanamadı.');
  }

  // Tamamlamayı reddet (POST /api/groups/completions/{id}/reject)
  Future<void> rejectCompletion(String token, int completionId) async {
    final url = Uri.parse(
      '${ApiConfig.baseUrl}/api/groups/completions/$completionId/reject',
    );
    final response = await http.post(
      url,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200) throw Exception('Reddedilemedi.');
  }
}
