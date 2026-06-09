import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/group.dart';
import '../models/task.dart';
import '../providers/auth_provider.dart';
import '../services/group_service.dart';
import 'create_task_screen.dart';
import 'task_detail_screen.dart';
import 'invite_member_screen.dart';

class GroupDetailScreen extends StatefulWidget {
  final Group group;
  const GroupDetailScreen({super.key, required this.group});

  @override
  State<GroupDetailScreen> createState() => _GroupDetailScreenState();
}

class _GroupDetailScreenState extends State<GroupDetailScreen> {
  final GroupService _service = GroupService();
  List<GroupMember> _members = [];
  List<Task> _tasks = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final token = context.read<AuthProvider>().token!;
      final members = await _service.fetchMembers(token, widget.group.id);
      final tasks = await _service.fetchGroupTasks(token, widget.group.id);
      if (!mounted) return;
      setState(() {
        _members = members;
        _tasks = tasks;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Veriler yüklenemedi.';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text(widget.group.name),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Görevler', icon: Icon(Icons.task_alt)),
              Tab(text: 'Üyeler', icon: Icon(Icons.people)),
            ],
          ),
          actions: [
            if (widget.group.isLeader)
              IconButton(
                icon: const Icon(Icons.person_add),
                tooltip: 'Üye Davet Et',
                onPressed: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => InviteMemberScreen(
                        groupId: widget.group.id,
                        groupName: widget.group.name,
                      ),
                    ),
                  );
                  _load(); // davetten dönünce üyeleri tazele (kabul edilirse görünür)
                },
              ),
            IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
          ],
        ),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
            ? Center(child: Text(_error!))
            : TabBarView(children: [_buildTasksTab(), _buildMembersTab()]),

        floatingActionButton: FloatingActionButton(
          onPressed: () async {
            await Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => CreateTaskScreen(groupId: widget.group.id),
              ),
            );
            _load(); // görev eklendikten sonra listeyi tazele
          },
          child: const Icon(Icons.add),
        ),
      ),
    );
  }

  Widget _buildTasksTab() {
    if (_tasks.isEmpty) {
      return const Center(child: Text('Bu grupta henüz görev yok.'));
    }
    return ListView.builder(
      itemCount: _tasks.length,
      itemBuilder: (context, index) {
        final task = _tasks[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          child: ListTile(
            title: Text(task.taskText),
            subtitle: Text(
              'Kategori: ${task.category}  •  Puan: ${task.difficultyScore}\n'
              '${task.completionCount} kişi tamamladı',
            ),
            isThreeLine: true,
            trailing: task.isVerifiedByMe
                ? const Icon(Icons.check_circle, color: Colors.green)
                : task.isPendingReviewByMe
                ? const Icon(Icons.hourglass_top, color: Colors.orange)
                : const Icon(Icons.chevron_right),
            onTap: () async {
              await Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => TaskDetailScreen(task: task)),
              );
              _load(); // detaydan dönünce grup görevlerini tazele
            },
          ),
        );
      },
    );
  }

  Widget _buildMembersTab() {
    if (_members.isEmpty) {
      return const Center(child: Text('Üye bulunamadı.'));
    }
    return ListView.builder(
      itemCount: _members.length,
      itemBuilder: (context, index) {
        final member = _members[index];
        return ListTile(
          leading: CircleAvatar(
            child: Text(
              member.username.isNotEmpty
                  ? member.username[0].toUpperCase()
                  : '?',
            ),
          ),
          title: Text(member.username),
          subtitle: Text('Seviye ${member.level}'),
        );
      },
    );
  }
}
