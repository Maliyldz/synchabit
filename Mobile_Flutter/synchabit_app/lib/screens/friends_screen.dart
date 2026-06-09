import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/friend_service.dart';

class FriendsScreen extends StatefulWidget {
  const FriendsScreen({super.key});

  @override
  State<FriendsScreen> createState() => _FriendsScreenState();
}

class _FriendsScreenState extends State<FriendsScreen> {
  final FriendService _service = FriendService();

  List<UserSummary> _friends = [];
  List<FriendRequest> _requests = [];
  bool _isLoading = true;

  String get _token => context.read<AuthProvider>().token!;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadAll());
  }

  Future<void> _loadAll() async {
    setState(() => _isLoading = true);
    try {
      final friends = await _service.getFriends(_token);
      final requests = await _service.getPendingRequests(_token);
      if (!mounted) return;
      setState(() {
        _friends = friends;
        _requests = requests;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Arkadaşlar'),
          bottom: TabBar(
            tabs: [
              const Tab(text: 'Arkadaşlarım'),
              Tab(
                text:
                    'İstekler${_requests.isNotEmpty ? ' (${_requests.length})' : ''}',
              ),
              const Tab(text: 'Ekle'),
            ],
          ),
        ),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : TabBarView(
                children: [
                  _buildFriendsTab(),
                  _buildRequestsTab(),
                  _buildAddTab(),
                ],
              ),
      ),
    );
  }

  Widget _buildFriendsTab() {
    if (_friends.isEmpty) {
      return const Center(
        child: Text('Henüz arkadaşın yok. "Ekle" sekmesinden ara.'),
      );
    }
    return RefreshIndicator(
      onRefresh: _loadAll,
      child: ListView.builder(
        itemCount: _friends.length,
        itemBuilder: (context, index) {
          final f = _friends[index];
          return ListTile(
            leading: CircleAvatar(
              child: Text(
                f.username.isNotEmpty ? f.username[0].toUpperCase() : '?',
              ),
            ),
            title: Text(f.username),
            subtitle: Text('Seviye ${f.level}'),
          );
        },
      ),
    );
  }

  Widget _buildRequestsTab() {
    if (_requests.isEmpty) {
      return const Center(child: Text('Bekleyen istek yok.'));
    }
    return ListView.builder(
      itemCount: _requests.length,
      itemBuilder: (context, index) {
        final r = _requests[index];
        return ListTile(
          leading: CircleAvatar(
            child: Text(
              r.senderUsername.isNotEmpty
                  ? r.senderUsername[0].toUpperCase()
                  : '?',
            ),
          ),
          title: Text(r.senderUsername),
          subtitle: Text('Seviye ${r.senderLevel}'),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              IconButton(
                icon: const Icon(Icons.check, color: Colors.green),
                onPressed: () async {
                  await _service.acceptRequest(_token, r.requestId);
                  _loadAll();
                },
              ),
              IconButton(
                icon: const Icon(Icons.close, color: Colors.red),
                onPressed: () async {
                  await _service.removeOrReject(_token, r.requestId);
                  _loadAll();
                },
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildAddTab() {
    return _AddFriendTab(service: _service, token: _token, onChanged: _loadAll);
  }
}

// Arama + istek gönderme — kendi state'i olduğu için ayrı widget
class _AddFriendTab extends StatefulWidget {
  final FriendService service;
  final String token;
  final VoidCallback onChanged;
  const _AddFriendTab({
    required this.service,
    required this.token,
    required this.onChanged,
  });

  @override
  State<_AddFriendTab> createState() => _AddFriendTabState();
}

class _AddFriendTabState extends State<_AddFriendTab> {
  final _searchController = TextEditingController();
  List<UserSummary> _results = [];
  bool _isSearching = false;
  String? _message;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _search() async {
    final q = _searchController.text.trim();
    if (q.isEmpty) return;
    setState(() {
      _isSearching = true;
      _message = null;
    });
    try {
      final results = await widget.service.searchUsers(widget.token, q);
      if (!mounted) return;
      setState(() {
        _results = results;
        _isSearching = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isSearching = false;
        _message = 'Arama başarısız.';
      });
    }
  }

  Future<void> _send(UserSummary user) async {
    try {
      final msg = await widget.service.sendRequest(widget.token, user.userId);
      if (!mounted) return;
      setState(() => _message = msg);
      widget.onChanged();
    } catch (e) {
      if (!mounted) return;
      setState(() => _message = e.toString().replaceAll('Exception: ', ''));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchController,
                  decoration: const InputDecoration(
                    hintText: 'Kullanıcı adı ara',
                    border: OutlineInputBorder(),
                  ),
                  onSubmitted: (_) => _search(),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton(onPressed: _search, child: const Text('Ara')),
            ],
          ),
          if (_message != null) ...[
            const SizedBox(height: 12),
            Text(_message!, style: const TextStyle(color: Colors.indigo)),
          ],
          const SizedBox(height: 12),
          Expanded(
            child: _isSearching
                ? const Center(child: CircularProgressIndicator())
                : _results.isEmpty
                ? const Center(child: Text('Aramak için kullanıcı adı yaz.'))
                : ListView.builder(
                    itemCount: _results.length,
                    itemBuilder: (context, index) {
                      final u = _results[index];
                      return ListTile(
                        leading: CircleAvatar(
                          child: Text(
                            u.username.isNotEmpty
                                ? u.username[0].toUpperCase()
                                : '?',
                          ),
                        ),
                        title: Text(u.username),
                        subtitle: Text('Seviye ${u.level}'),
                        trailing: IconButton(
                          icon: const Icon(Icons.person_add),
                          onPressed: () => _send(u),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
