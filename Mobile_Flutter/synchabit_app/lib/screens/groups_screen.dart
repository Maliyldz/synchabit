import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/group_provider.dart';
import 'create_group_screen.dart';
import 'group_detail_screen.dart';
import 'group_invites_screen.dart';
import '../services/group_service.dart';
import '../widgets/empty_state.dart';

class GroupsScreen extends StatefulWidget {
  const GroupsScreen({super.key});

  @override
  State<GroupsScreen> createState() => _GroupsScreenState();
}

class _GroupsScreenState extends State<GroupsScreen> {
  bool _hasInvites = false;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final token = context.read<AuthProvider>().token;
    if (token == null) return;

    // Grupları yükle
    context.read<GroupProvider>().loadGroups(token);

    // Bekleyen davet var mı kontrol et (rozet için)
    try {
      final invites = await GroupService().fetchMyInvites(token);
      if (!mounted) return;
      setState(() => _hasInvites = invites.isNotEmpty);
    } catch (_) {
      if (!mounted) return;
      setState(() => _hasInvites = false); // hata olursa rozet gösterme
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<GroupProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Gruplarım'),
        actions: [
          Badge(
            isLabelVisible: _hasInvites,
            smallSize: 8,
            child: IconButton(
              icon: const Icon(Icons.mail_outline),
              tooltip: 'Grup Davetleri',
              onPressed: () async {
                await Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const GroupInvitesScreen()),
                );
                _load();
              },
            ),
          ),
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
      ),
      body: _buildBody(provider),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await Navigator.of(
            context,
          ).push(MaterialPageRoute(builder: (_) => const CreateGroupScreen()));
          _load(); // oluşturma ekranından dönünce tazele
        },
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody(GroupProvider provider) {
    if (provider.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.errorMessage != null) {
      return Center(child: Text(provider.errorMessage!));
    }
    if (provider.groups.isEmpty) {
      return const EmptyState(
        icon: Icons.groups_2,
        title: 'Henüz grubun yok',
        message: 'Bir grup oluştur ya da gelen davetlere göz at.',
      );
    }
    return ListView.builder(
      itemCount: provider.groups.length,
      itemBuilder: (context, index) {
        final group = provider.groups[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          child: ListTile(
            leading: const Icon(Icons.groups),
            title: Text(group.name),
            subtitle: Text(
              group.description.isEmpty ? 'Açıklama yok' : group.description,
            ),
            trailing: group.isLeader
                ? const Chip(label: Text('Lider'), padding: EdgeInsets.zero)
                : const Icon(Icons.chevron_right),
            onTap: () async {
              await Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => GroupDetailScreen(group: group),
                ),
              );
              _load();
            },
          ),
        );
      },
    );
  }
}
