import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/task_provider.dart';
import 'create_task_screen.dart';
import 'task_detail_screen.dart';
import '../widgets/empty_state.dart';
import '../models/task_category.dart';
import '../models/task.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    // Ekran ilk açıldığında görevleri çek.
    // addPostFrameCallback: build bitmeden provider'a dokunmamak için.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadTasks();
    });
  }

  void _loadTasks() {
    final token = context.read<AuthProvider>().token;
    if (token != null) {
      context.read<TaskProvider>().loadTasks(token);
    }
  }

  String _formatDate(DateTime d) {
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(d.day)}.${two(d.month)}.${d.year} ${two(d.hour)}:${two(d.minute)}';
  }

  @override
  Widget build(BuildContext context) {
    final taskProvider = context.watch<TaskProvider>();

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Görevlerim'),
          actions: [
            IconButton(icon: const Icon(Icons.refresh), onPressed: _loadTasks),
          ],
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Aktif'),
              Tab(text: 'Tamamlanan'),
            ],
          ),
        ),

        body: _buildBody(taskProvider),
        floatingActionButton: FloatingActionButton(
          onPressed: () async {
            // Oluşturma ekranından dönünce listeyi tazele
            await Navigator.of(
              context,
            ).push(MaterialPageRoute(builder: (_) => const CreateTaskScreen()));
            _loadTasks();
          },
          child: const Icon(Icons.add),
        ),
      ),
    );
  }

  Widget _buildBody(TaskProvider taskProvider) {
    if (taskProvider.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (taskProvider.errorMessage != null) {
      return Center(child: Text(taskProvider.errorMessage!));
    }

    // TAMAMLANAN: sadece onaylanmış, son tamamlanan üstte
    final tamamlanan =
        taskProvider.tasks.where((t) => t.isVerifiedByMe).toList()
          ..sort((a, b) {
            // completedAt'e göre tersten (yeni → eski). Null en alta.
            final ad = a.completedAt;
            final bd = b.completedAt;
            if (ad == null && bd == null) return 0;
            if (ad == null) return 1;
            if (bd == null) return -1;
            return bd.compareTo(ad); // ters sıra
          });
    // AKTİF: tamamlanmamışlar. Süresi geçmeyenler üstte, geçenler altta.
    final aktif = taskProvider.tasks.where((t) => !t.isVerifiedByMe).toList()
      ..sort((a, b) {
        // 1) Süresi geçen görevler en alta
        if (a.isExpired && !b.isExpired) return 1;
        if (!a.isExpired && b.isExpired) return -1;

        // 2) Aynı grupta → oluşturulma tarihine göre yeni üstte
        final ad = a.createdAt;
        final bd = b.createdAt;
        if (ad == null && bd == null) return 0;
        if (ad == null) return 1;
        if (bd == null) return -1;
        return bd.compareTo(ad); // ters sıra (yeni → eski)
      });

    return TabBarView(
      children: [
        _buildTaskList(aktif, isCompletedTab: false),
        _buildTaskList(tamamlanan, isCompletedTab: true),
      ],
    );
  }

  Widget _buildTaskList(List<Task> tasks, {required bool isCompletedTab}) {
    if (tasks.isEmpty) {
      return EmptyState(
        icon: isCompletedTab ? Icons.check_circle_outline : Icons.task_alt,
        title: isCompletedTab
            ? 'Henüz tamamlanan görev yok'
            : 'Aktif görevin yok',
        message: isCompletedTab
            ? 'Tamamladığın görevler burada görünür.'
            : 'İlk görevini eklemek için + butonuna dokun.',
      );
    }
    return ListView.builder(
      itemCount: tasks.length,
      itemBuilder: (context, index) {
        final task = tasks[index];
        return Opacity(
          opacity: task.isExpired ? 0.55 : 1.0,
          child: Card(
            margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: ListTile(
              title: Text(task.taskText),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Kategori: ${categoryLabel(task.category)}  •  Puan: ${task.difficultyScore}',
                  ),
                  if (task.dueDate != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(
                        task.isExpired
                            ? '⏰ Süresi doldu'
                            : 'Son tarih: ${_formatDate(task.dueDate!)}',
                        style: TextStyle(
                          fontSize: 12,
                          color: task.isExpired
                              ? Colors.red
                              : Colors.grey.shade600,
                          fontWeight: task.isExpired
                              ? FontWeight.bold
                              : FontWeight.normal,
                        ),
                      ),
                    ),
                ],
              ),
              trailing: task.isVerifiedByMe
                  ? const Icon(Icons.check_circle, color: Colors.green)
                  : task.isPendingReviewByMe
                  ? const Icon(Icons.hourglass_top, color: Colors.orange)
                  : task.isExpired
                  ? const Icon(Icons.lock_clock, color: Colors.red)
                  : const Icon(Icons.chevron_right),
              onTap: () async {
                await Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => TaskDetailScreen(task: task),
                  ),
                );
                _loadTasks();
              },
            ),
          ),
        );
      },
    );
  }
}
