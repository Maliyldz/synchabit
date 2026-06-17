import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../models/task.dart';
import '../models/task_category.dart';
import '../providers/auth_provider.dart';
import '../providers/task_provider.dart';
import '../services/task_service.dart';

class TaskDetailScreen extends StatefulWidget {
  final Task task;
  const TaskDetailScreen({super.key, required this.task});

  @override
  State<TaskDetailScreen> createState() => _TaskDetailScreenState();
}

class _TaskDetailScreenState extends State<TaskDetailScreen> {
  final ImagePicker _picker = ImagePicker();
  bool _isUploading = false;
  VerifyResult? _result;
  String? _errorMessage;
  bool _justCompleted = false;

  // Bu görevin kategorisinde görsel doğrulama var mı?
  bool get _hasImageVerification {
    final cat = kTaskCategories.firstWhere(
      (c) => c.value == widget.task.category,
      orElse: () =>
          const TaskCategory(label: '', value: '', hasImageVerification: false),
    );
    return cat.hasImageVerification;
  }

  Future<void> _pickAndVerify(ImageSource source) async {
    try {
      final picked = await _picker.pickImage(source: source, imageQuality: 85);
      if (picked == null) return; // kullanıcı vazgeçti

      setState(() {
        _isUploading = true;
        _errorMessage = null;
        _result = null;
      });

      final token = context.read<AuthProvider>().token!;
      final result = await context.read<TaskProvider>().verifyTaskImage(
        token: token,
        taskId: widget.task.id,
        imageFile: File(picked.path),
      );

      if (!mounted) return;
      setState(() {
        _isUploading = false;
        _result = result;
        // Verified veya NeedsReview ise tamamlama oluştu → butonu gizle
        if (result.status == 'Verified' || result.status == 'NeedsReview') {
          _justCompleted = true;
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isUploading = false;
        _errorMessage = e.toString().replaceAll('Exception: ', '');
      });
    }
  }

  void _showSourceSheet() {
    showModalBottomSheet(
      context: context,
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt),
              title: const Text('Kamera'),
              onTap: () {
                Navigator.pop(context);
                _pickAndVerify(ImageSource.camera);
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Galeri'),
              onTap: () {
                Navigator.pop(context);
                _pickAndVerify(ImageSource.gallery);
              },
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime d) {
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(d.day)}.${two(d.month)}.${d.year} ${two(d.hour)}:${two(d.minute)}';
  }

  @override
  Widget build(BuildContext context) {
    final task = widget.task;

    return Scaffold(
      appBar: AppBar(title: const Text('Görev Detayı')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              task.taskText,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Kategori: ${categoryLabel(task.category)}  •  Puan: ${task.difficultyScore}',
            ),
            const SizedBox(height: 8),
            if (task.dueDate != null) ...[
              Row(
                children: [
                  Icon(
                    Icons.event,
                    size: 16,
                    color: task.isExpired ? Colors.red : Colors.grey.shade700,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'Son tarih: ${_formatDate(task.dueDate!)}',
                    style: TextStyle(
                      fontSize: 13,
                      color: task.isExpired ? Colors.red : Colors.grey.shade700,
                      fontWeight: task.isExpired
                          ? FontWeight.bold
                          : FontWeight.normal,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
            ],
            if (task.isVerifiedByMe)
              const Chip(
                label: Text('Tamamlandı'),
                backgroundColor: Color(0xFFD7F5DD),
              ),
            const Divider(height: 32),
            if (task.isExpired && !task.isDoneByMe)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.lock_clock, color: Colors.red),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Bu görevin süresi doldu, artık tamamlanamaz.',
                        style: TextStyle(color: Colors.red),
                      ),
                    ),
                  ],
                ),
              )
            else if (task.isVerifiedByMe || _result?.status == 'Verified')
              const Text('Bu görevi tamamladın.')
            else if (task.isPendingReviewByMe ||
                _result?.status == 'NeedsReview')
              const Text(
                'Fotoğrafın gönderildi, grup liderinin onayı bekleniyor.',
              )
            else ...[
              // Kategoriye göre bilgi notu
              Text(
                _hasImageVerification
                    ? '📷 Fotoğrafın yapay zeka ile doğrulanacak.'
                    : 'ℹ️ Bu kategoride yapay zeka doğrulaması yok; fotoğrafın grup liderinin onayına gidecek.',
                style: TextStyle(fontSize: 13, color: Colors.grey.shade700),
              ),
              const SizedBox(height: 12),
              const Text(
                'Kanıt fotoğrafı yükle',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _isUploading ? null : _showSourceSheet,
                  icon: const Icon(Icons.add_a_photo),
                  label: Text(
                    _isUploading ? 'Yükleniyor...' : 'Fotoğraf Yükle',
                  ),
                ),
              ),
            ],

            if (_isUploading) ...[
              const SizedBox(height: 24),
              const Center(child: CircularProgressIndicator()),
            ],

            if (_result != null) ...[
              const SizedBox(height: 24),
              _buildResultBox(_result!),
            ],

            if (_errorMessage != null) ...[
              const SizedBox(height: 24),
              _buildErrorBox(_errorMessage!),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildResultBox(VerifyResult result) {
    // Üç durumu farklı renk/mesajla göster
    late Color color;
    late IconData icon;
    late String title;

    switch (result.status) {
      case 'Verified':
        color = Colors.green;
        icon = Icons.check_circle;
        title = 'Doğrulandı! Görev tamamlandı.';
        break;
      case 'NeedsReview':
        color = Colors.orange;
        icon = Icons.hourglass_top;
        title = 'AI emin olamadı, manuel onaya düştü.';
        break;
      default: // Rejected
        color = Colors.red;
        icon = Icons.cancel;
        title = 'Fotoğraf bu göreve uymuyor.';
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(fontWeight: FontWeight.bold, color: color),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(result.reason),
        ],
      ),
    );
  }

  Widget _buildErrorBox(String message) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.red.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.red.shade200),
      ),
      child: Text(message, style: TextStyle(color: Colors.red.shade900)),
    );
  }
}
