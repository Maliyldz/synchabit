import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/friend_service.dart';
import '../services/group_service.dart';

class InviteMemberScreen extends StatefulWidget {
  final int groupId;
  final String groupName;
  const InviteMemberScreen({
    super.key,
    required this.groupId,
    required this.groupName,
  });

  @override
  State<InviteMemberScreen> createState() => _InviteMemberScreenState();
}

class _InviteMemberScreenState extends State<InviteMemberScreen> {
  final FriendService _friendService = FriendService();
  final GroupService _groupService = GroupService();

  List<UserSummary> _friends = [];
  bool _isLoading = true;
  final Set<int> _invited = {}; // davet edilenleri işaretle

  String get _token => context.read<AuthProvider>().token!;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    try {
      final friends = await _friendService.getFriends(_token);
      if (!mounted) return;
      setState(() {
        _friends = friends;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<void> _invite(UserSummary friend) async {
    try {
      final msg = await _groupService.inviteToGroup(
        token: _token,
        groupId: widget.groupId,
        friendId: friend.userId,
      );
      if (!mounted) return;
      setState(() => _invited.add(friend.userId));
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceAll('Exception: ', ''))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('${widget.groupName} — Davet Et')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _friends.isEmpty
          ? const Center(
              child: Text(
                'Davet edebileceğin arkadaşın yok.\nÖnce arkadaş ekle.',
                textAlign: TextAlign.center,
              ),
            )
          : ListView.builder(
              itemCount: _friends.length,
              itemBuilder: (context, index) {
                final f = _friends[index];
                final alreadyInvited = _invited.contains(f.userId);
                return ListTile(
                  leading: CircleAvatar(
                    child: Text(
                      f.username.isNotEmpty ? f.username[0].toUpperCase() : '?',
                    ),
                  ),
                  title: Text(f.username),
                  subtitle: Text('Seviye ${f.level}'),
                  trailing: alreadyInvited
                      ? const Chip(label: Text('Davet edildi'))
                      : FilledButton(
                          onPressed: () => _invite(f),
                          child: const Text('Davet Et'),
                        ),
                );
              },
            ),
    );
  }
}
