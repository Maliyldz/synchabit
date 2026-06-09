import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/group.dart';
import '../providers/auth_provider.dart';
import '../services/group_service.dart';

class GroupInvitesScreen extends StatefulWidget {
  const GroupInvitesScreen({super.key});

  @override
  State<GroupInvitesScreen> createState() => _GroupInvitesScreenState();
}

class _GroupInvitesScreenState extends State<GroupInvitesScreen> {
  final GroupService _service = GroupService();
  List<GroupInvite> _invites = [];
  bool _isLoading = true;

  String get _token => context.read<AuthProvider>().token!;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final invites = await _service.fetchMyInvites(_token);
      if (!mounted) return;
      setState(() {
        _invites = invites;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<void> _accept(GroupInvite invite) async {
    try {
      await _service.acceptInvite(_token, invite.inviteId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${invite.groupName} grubuna katıldın.')),
      );
      _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Davet kabul edilemedi.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Grup Davetleri')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _invites.isEmpty
          ? const Center(child: Text('Bekleyen grup daveti yok.'))
          : ListView.builder(
              itemCount: _invites.length,
              itemBuilder: (context, index) {
                final inv = _invites[index];
                return Card(
                  margin: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 6,
                  ),
                  child: ListTile(
                    leading: const Icon(Icons.group_add),
                    title: Text(inv.groupName),
                    subtitle: Text('${inv.inviterUsername} davet etti'),
                    trailing: FilledButton(
                      onPressed: () => _accept(inv),
                      child: const Text('Katıl'),
                    ),
                  ),
                );
              },
            ),
    );
  }
}
