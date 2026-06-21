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
import '../models/task_category.dart';

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

  String _formatDate(DateTime d) {
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(d.day)}.${two(d.month)}.${d.year} ${two(d.hour)}:${two(d.minute)}';
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
        icon: Icons.task_alt,
        title: 'Henüz görev yok',
        message: 'İlk görevi eklemek için + butonuna dokun.',
      );
    }

    // TAMAMLANAN: onaylanmış, son tamamlanan üstte
    final tamamlanan = _tasks.where((t) => t.isVerifiedByMe).toList()
      ..sort((a, b) {
        final ad = a.completedAt;
        final bd = b.completedAt;
        if (ad == null && bd == null) return 0;
        if (ad == null) return 1;
        if (bd == null) return -1;
        return bd.compareTo(ad);
      });

    // AKTİF: tamamlanmamışlar. Süresi geçmeyenler üstte (yeni→eski), geçenler altta
    final aktif = _tasks.where((t) => !t.isVerifiedByMe).toList()
      ..sort((a, b) {
        if (a.isExpired && !b.isExpired) return 1;
        if (!a.isExpired && b.isExpired) return -1;
        final ad = a.createdAt;
        final bd = b.createdAt;
        if (ad == null && bd == null) return 0;
        if (ad == null) return 1;
        if (bd == null) return -1;
        return bd.compareTo(ad);
      });

    return ListView(
      children: [
        if (aktif.isNotEmpty) ...[
          _sectionHeader('Aktif (${aktif.length})'),
          ...aktif.map(_buildTaskCard),
        ],
        if (tamamlanan.isNotEmpty) ...[
          _sectionHeader('Tamamlanan (${tamamlanan.length})'),
          ...tamamlanan.map(_buildTaskCard),
        ],
        const SizedBox(height: 12),
      ],
    );
  }

  // Bölüm başlığı
  Widget _sectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.bold,
          color: Colors.grey.shade700,
        ),
      ),
    );
  }

  // Tek görev kartı (hem aktif hem tamamlanan bölümünde kullanılır)
  Widget _buildTaskCard(Task task) {
    return Opacity(
      opacity: task.isExpired && !task.isVerifiedByMe ? 0.55 : 1.0,
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
              Text('${task.completionCount} kişi tamamladı'),
              if (task.dueDate != null)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text(
                    task.isExpired
                        ? '⏰ Süresi doldu'
                        : 'Son tarih: ${_formatDate(task.dueDate!)}',
                    style: TextStyle(
                      fontSize: 12,
                      color: task.isExpired ? Colors.red : Colors.grey.shade600,
                      fontWeight: task.isExpired
                          ? FontWeight.bold
                          : FontWeight.normal,
                    ),
                  ),
                ),
            ],
          ),
          isThreeLine: true,
          trailing: task.isVerifiedByMe
              ? const Icon(Icons.check_circle, color: Colors.green)
              : task.isPendingReviewByMe
              ? const Icon(Icons.hourglass_top, color: Colors.orange)
              : task.isExpired
              ? const Icon(Icons.lock_clock, color: Colors.red)
              : const Icon(Icons.chevron_right),
          onTap: () async {
            await Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => TaskDetailScreen(task: task)),
            );
            _load();
          },
        ),
      ),
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
