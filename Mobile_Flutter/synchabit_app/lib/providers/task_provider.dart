import 'package:flutter/material.dart';
import '../models/task.dart';
import '../services/task_service.dart';

class TaskProvider extends ChangeNotifier {
  final TaskService _taskService = TaskService();

  List<Task> _tasks = [];
  bool _isLoading = false;
  String? _errorMessage;

  List<Task> get tasks => _tasks;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  // Görevleri backend'den çek
  Future<void> loadTasks(String token) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _tasks = await _taskService.fetchTasks(token);
    } catch (e) {
      _errorMessage = 'Görevler yüklenemedi.';
    }

    _isLoading = false;
    notifyListeners();
  }

  // Yeni görev oluştur. Başarılıysa listeye ekler ve true döner.
  // NLP reddederse false döner, errorMessage dolar.
  Future<CreateTaskResult> createTask({
    required String token,
    required String taskText,
    required String category,
    required int difficultyScore,
  }) async {
    final result = await _taskService.createTask(
      token: token,
      taskText: taskText,
      category: category,
      difficultyScore: difficultyScore,
    );

    if (result.success && result.task != null) {
      _tasks.add(result.task!);
      notifyListeners();
    }
    return result;
  }
}
