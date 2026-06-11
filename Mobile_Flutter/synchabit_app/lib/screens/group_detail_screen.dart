import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/group.dart';
import '../models/task.dart';
import '../providers/auth_provider.dart';
import '../services/group_service.dart';
import 'create_task_screen.dart';
import 'task_detail_screen.dart';
import 'invite_member_screen.dart';
import 'group_approvals_screen.dart';
import '../widgets/empty_state.dart';

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
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: Text(widget.group.name),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Görevler', icon: Icon(Icons.task_alt)),
              Tab(text: 'Üyeler', icon: Icon(Icons.people)),
              Tab(text: 'Sıralama', icon: Icon(Icons.leaderboard)),
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
            if (widget.group.isLeader)
              IconButton(
                icon: const Icon(Icons.fact_check_outlined),
                tooltip: 'Onaylar',
                onPressed: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => GroupApprovalsScreen(
                        groupId: widget.group.id,
                        groupName: widget.group.name,
                      ),
                    ),
                  );
                  _load(); // onaydan dönünce görev durumlarını tazele
                },
              ),
            IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
          ],
        ),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
            ? Center(child: Text(_error!))
            : TabBarView(
                children: [
                  _buildTasksTab(),
                  _buildMembersTab(),
                  _buildLeaderboardTab(),
                ],
              ),
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
      return const EmptyState(
        icon: Icons.person_outline,
        title: 'Üye bulunamadı',
      );
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
      return const EmptyState(
        icon: Icons.person_outline,
        title: 'Üye bulunamadı',
      );
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

  Widget _buildLeaderboardTab() {
    return FutureBuilder<List<LeaderboardEntry>>(
      future: _service.fetchLeaderboard(
        context.read<AuthProvider>().token!,
        widget.group.id,
      ),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return const Center(child: Text('Sıralama yüklenemedi.'));
        }
        final entries = snapshot.data ?? [];
        if (entries.isEmpty) {
          return const EmptyState(
            icon: Icons.leaderboard_outlined,
            title: 'Sıralama boş',
            message: 'Görev tamamlandıkça sıralama oluşur.',
          );
        }
        return ListView.builder(
          itemCount: entries.length,
          itemBuilder: (context, index) {
            final e = entries[index];
            final rank = index + 1;
            return ListTile(
              leading: _rankBadge(rank),
              title: Text(e.username),
              trailing: Text(
                '${e.groupXp} XP',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            );
          },
        );
      },
    );
  }

  Widget _rankBadge(int rank) {
    Color color;
    switch (rank) {
      case 1:
        color = const Color(0xFFFFD700); // altın
        break;
      case 2:
        color = const Color(0xFFC0C0C0); // gümüş
        break;
      case 3:
        color = const Color(0xFFCD7F32); // bronz
        break;
      default:
        return CircleAvatar(
          backgroundColor: Colors.grey.shade300,
          child: Text('$rank'),
        );
    }
    return CircleAvatar(
      backgroundColor: color,
      child: Text(
        '$rank',
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
