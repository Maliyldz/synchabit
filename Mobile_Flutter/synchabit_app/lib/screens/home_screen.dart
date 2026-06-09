import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/task_provider.dart';
import 'login_screen.dart';
import 'create_task_screen.dart';
import 'task_detail_screen.dart';

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

  @override
  Widget build(BuildContext context) {
    final taskProvider = context.watch<TaskProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Görevlerim'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadTasks),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () {
              context.read<AuthProvider>().logout();
              Navigator.of(context).pushReplacement(
                MaterialPageRoute(builder: (_) => const LoginScreen()),
              );
            },
          ),
        ],
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
    );
  }

  Widget _buildBody(TaskProvider taskProvider) {
    if (taskProvider.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (taskProvider.errorMessage != null) {
      return Center(child: Text(taskProvider.errorMessage!));
    }
    if (taskProvider.tasks.isEmpty) {
      return const Center(child: Text('Henüz görevin yok. + ile ekle.'));
    }
    return ListView.builder(
      itemCount: taskProvider.tasks.length,
      itemBuilder: (context, index) {
        final task = taskProvider.tasks[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          child: ListTile(
            title: Text(task.taskText),
            subtitle: Text(
              'Kategori: ${task.category}  •  Puan: ${task.difficultyScore}',
            ),
            trailing: task.isVerifiedByMe
                ? const Icon(Icons.check_circle, color: Colors.green)
                : const Icon(Icons.chevron_right),

            onTap: () async {
              await Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => TaskDetailScreen(task: task)),
              );
              _loadTasks(); // detaydan dönünce listeyi tazele
            },
          ),
        );
      },
    );
  }
}
