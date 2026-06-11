import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/profile_service.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final ProfileService _service = ProfileService();
  ProfileData? _profile;
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
      final profile = await _service.fetchProfile(_token);
      if (!mounted) return;
      setState(() {
        _profile = profile;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Profil'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Çıkış Yap',
            onPressed: () => context.read<AuthProvider>().logout(),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _profile == null
          ? const Center(child: Text('Profil yüklenemedi.'))
          : _buildProfile(_profile!),
    );
  }

  Widget _buildProfile(ProfileData p) {
    // İlerleme oranı: bu seviyede toplanan / bu seviyenin boyu
    final double progress = p.xpForThisLevel > 0
        ? (p.xpInCurrentLevel / p.xpForThisLevel).clamp(0.0, 1.0)
        : 0.0;

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          const SizedBox(height: 16),
          // Avatar
          CircleAvatar(
            radius: 48,
            child: Text(
              p.username.isNotEmpty ? p.username[0].toUpperCase() : '?',
              style: const TextStyle(fontSize: 36),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            p.username,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          // Seviye rozeti
          Center(
            child: Chip(
              avatar: const Icon(Icons.star, size: 18, color: Colors.amber),
              label: Text('Seviye ${p.level}'),
            ),
          ),
          const SizedBox(height: 32),
          // İlerleme çubuğu
          Text(
            'Seviye ${p.level} → ${p.level + 1}',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 14,
              backgroundColor: Colors.grey.shade300,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '${p.xpInCurrentLevel} / ${p.xpForThisLevel} XP'
            '  (sonraki seviyeye ${p.xpRemaining} XP)',
            style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
          ),
          const SizedBox(height: 32),
          // Toplam XP kartı
          Card(
            child: ListTile(
              leading: const Icon(Icons.bolt, color: Colors.amber),
              title: const Text('Toplam XP'),
              trailing: Text(
                '${p.totalXp}',
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
