import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/task_category.dart';
import '../providers/auth_provider.dart';
import '../providers/task_provider.dart';
import '../services/group_service.dart';
import '../services/task_service.dart';

class CreateTaskScreen extends StatefulWidget {
  // groupId null ise bireysel görev, doluysa gruba görev eklenir
  final int? groupId;
  const CreateTaskScreen({super.key, this.groupId});

  @override
  State<CreateTaskScreen> createState() => _CreateTaskScreenState();
}

class _CreateTaskScreenState extends State<CreateTaskScreen> {
  final _taskTextController = TextEditingController();
  final _pointsController = TextEditingController(text: '10');
  final GroupService _groupService = GroupService();

  TaskCategory _selectedCategory = kTaskCategories.first;
  bool _isSubmitting = false;
  String? _errorMessage;

  bool get _isGroupTask => widget.groupId != null;

  DateTime? _dueDate; // opsiyonel son tarih (null = süresiz)

  @override
  void dispose() {
    _taskTextController.dispose();
    _pointsController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final text = _taskTextController.text.trim();
    if (text.isEmpty) {
      setState(() => _errorMessage = 'Görev metni boş olamaz.');
      return;
    }

    final points = int.tryParse(_pointsController.text.trim());
    if (points == null || points < 10 || points > 100) {
      setState(
        () => _errorMessage = 'Puan 10 ile 100 arasında bir sayı olmalı.',
      );
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    final token = context.read<AuthProvider>().token!;
    CreateTaskResult result;

    if (_isGroupTask) {
      // Gruba görev ekle
      result = await _groupService.addGroupTask(
        token: token,
        groupId: widget.groupId!,
        taskText: text,
        category: _selectedCategory.value,
        difficultyScore: points,
        dueDate: _dueDate,
      );
    } else {
      // Bireysel görev (eski davranış)
      result = await context.read<TaskProvider>().createTask(
        token: token,
        taskText: text,
        category: _selectedCategory.value,
        difficultyScore: points,
        dueDate: _dueDate,
      );
    }

    if (!mounted) return;

    if (result.success) {
      Navigator.of(context).pop();
    } else {
      setState(() {
        _isSubmitting = false;
        _errorMessage = result.errorMessage;
      });
    }
  }

  Future<void> _pickDueDate() async {
    final now = DateTime.now();

    // 1. Tarih seç (bugünden itibaren, 1 yıl ileriye kadar)
    final date = await showDatePicker(
      context: context,
      initialDate: now,
      firstDate: now, // geçmiş seçilemez
      lastDate: now.add(const Duration(days: 365)),
    );
    if (date == null) return; // vazgeçti

    if (!mounted) return;

    // 2. Saat seç
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.now(),
      initialEntryMode: TimePickerEntryMode.input,
      builder: (context, child) {
        return MediaQuery(
          data: MediaQuery.of(context).copyWith(alwaysUse24HourFormat: true),
          child: child!,
        );
      },
    );
    if (time == null) return; // vazgeçti

    final selected = DateTime(
      date.year,
      date.month,
      date.day,
      time.hour,
      time.minute,
    );

    // Seçilen tarih+saat geçmişte mi? (bugün + geçmiş saat durumu)
    if (selected.isBefore(DateTime.now())) {
      if (!mounted) return;
      setState(() {
        _errorMessage =
            'Son tarih geçmiş bir zaman olamaz. Lütfen ileri bir zaman seç.';
      });
      return; // _dueDate'i set etme
    }

    if (!mounted) return;
    setState(() {
      _dueDate = selected;
      _errorMessage = null; // varsa eski hatayı temizle
    });
  }

  String _formatDueDate(DateTime d) {
    final two = (int n) => n.toString().padLeft(2, '0');
    return '${two(d.day)}.${two(d.month)}.${d.year}  ${two(d.hour)}:${two(d.minute)}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_isGroupTask ? 'Gruba Görev Ekle' : 'Yeni Görev'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Görev metni'),
              const SizedBox(height: 8),
              TextField(
                controller: _taskTextController,
                maxLines: 3,
                decoration: const InputDecoration(
                  hintText: 'Örn: 30 dakika kitap oku',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 20),
              const Text('Kategori'),
              const SizedBox(height: 8),
              DropdownButtonFormField<TaskCategory>(
                initialValue: _selectedCategory,
                decoration: const InputDecoration(border: OutlineInputBorder()),
                items: kTaskCategories
                    .map(
                      (c) => DropdownMenuItem(value: c, child: Text(c.label)),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value != null) setState(() => _selectedCategory = value);
                },
              ),
              const SizedBox(height: 8),
              Text(
                _selectedCategory.hasImageVerification
                    ? '📷 Bu görev tamamlanırken fotoğrafla doğrulanacak.'
                    : 'ℹ️ Bu kategoride görsel doğrulama yok.',
                style: TextStyle(
                  fontSize: 13,
                  color: _selectedCategory.hasImageVerification
                      ? Colors.indigo
                      : Colors.grey.shade600,
                ),
              ),
              const SizedBox(height: 20),
              const Text('Puan (10-100)'),
              const SizedBox(height: 8),
              TextField(
                controller: _pointsController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  hintText: '10-100 arası',
                  border: OutlineInputBorder(),
                ),
              ),
              const Text('Son tarih (opsiyonel)'),
              const SizedBox(height: 8),
              if (_dueDate == null)
                OutlinedButton.icon(
                  onPressed: _pickDueDate,
                  icon: const Icon(Icons.event),
                  label: const Text('Son tarih ekle'),
                )
              else
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 14,
                        ),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.grey.shade400),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.event, size: 18),
                            const SizedBox(width: 8),
                            Text(_formatDueDate(_dueDate!)),
                          ],
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      tooltip: 'Son tarihi kaldır',
                      onPressed: () => setState(() => _dueDate = null),
                    ),
                  ],
                ),
              const SizedBox(height: 20),
              const SizedBox(height: 20),
              if (_errorMessage != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: TextStyle(color: Colors.red.shade900),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _isSubmitting ? null : _submit,
                  child: _isSubmitting
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Text(_isGroupTask ? 'Gruba Ekle' : 'Görevi Oluştur'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
