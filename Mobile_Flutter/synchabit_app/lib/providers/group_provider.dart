import 'package:flutter/material.dart';
import '../models/group.dart';
import '../services/group_service.dart';

class GroupProvider extends ChangeNotifier {
  final GroupService _groupService = GroupService();

  List<Group> _groups = [];
  bool _isLoading = false;
  String? _errorMessage;

  List<Group> get groups => _groups;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> loadGroups(String token) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      _groups = await _groupService.fetchMyGroups(token);
    } catch (e) {
      _errorMessage = 'Gruplar yüklenemedi.';
    }
    _isLoading = false;
    notifyListeners();
  }

  // Grup oluştur, başarılıysa listeyi tazele
  Future<bool> createGroup({
    required String token,
    required String name,
    required String description,
  }) async {
    try {
      await _groupService.createGroup(
        token: token,
        name: name,
        description: description,
      );
      await loadGroups(token); // yeni grup listede görünsün
      return true;
    } catch (e) {
      _errorMessage = 'Grup oluşturulamadı.';
      notifyListeners();
      return false;
    }
  }
}
