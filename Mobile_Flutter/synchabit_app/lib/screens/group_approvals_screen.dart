import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/api_config.dart';
import '../models/group.dart';
import '../providers/auth_provider.dart';
import '../services/group_service.dart';
import '../widgets/empty_state.dart';
import '../models/task_category.dart';

class GroupApprovalsScreen extends StatefulWidget {
  final int groupId;
  final String groupName;
  const GroupApprovalsScreen({
    super.key,
    required this.groupId,
    required this.groupName,
  });

  @override
  State<GroupApprovalsScreen> createState() => _GroupApprovalsScreenState();
}

class _GroupApprovalsScreenState extends State<GroupApprovalsScreen> {
  final GroupService _service = GroupService();
  List<PendingApproval> _pending = [];
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
      final pending = await _service.fetchPendingApprovals(
        _token,
        widget.groupId,
      );
      if (!mounted) return;
      setState(() {
        _pending = pending;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<void> _approve(PendingApproval p) async {
    try {
      await _service.approveCompletion(_token, p.completionId);
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Onaylandı.')));
      _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Onaylanamadı.')));
    }
  }

  Future<void> _reject(PendingApproval p) async {
    try {
      await _service.rejectCompletion(_token, p.completionId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Reddedildi. Üye tekrar deneyebilir.')),
      );
      _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Reddedilemedi.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('${widget.groupName} — Onaylar')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _pending.isEmpty
          ? const EmptyState(
              icon: Icons.fact_check_outlined,
              title: 'Onay bekleyen yok',
              message: 'Tüm tamamlamalar değerlendirildi.',
            )
          : ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: _pending.length,
              itemBuilder: (context, index) {
                final p = _pending[index];
                return Card(
                  margin: const EdgeInsets.only(bottom: 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Kanıt fotoğrafı
                      if (p.proofImagePath != null)
                        ClipRRect(
                          borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(12),
                          ),
                          child: Image.network(
                            '${ApiConfig.baseUrl}${p.proofImagePath}',
                            height: 220,
                            width: double.infinity,
                            fit: BoxFit.cover,
                            loadingBuilder: (context, child, progress) {
                              if (progress == null) return child;
                              return const SizedBox(
                                height: 220,
                                child: Center(
                                  child: CircularProgressIndicator(),
                                ),
                              );
                            },
                            errorBuilder: (context, error, stack) =>
                                const SizedBox(
                                  height: 220,
                                  child: Center(
                                    child: Text('Fotoğraf yüklenemedi'),
                                  ),
                                ),
                          ),
                        ),
                      Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              p.taskText,
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              categoryLabel(p.category),
                              style: const TextStyle(color: Colors.black54),
                            ),
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Expanded(
                                  child: FilledButton.icon(
                                    onPressed: () => _approve(p),
                                    icon: const Icon(Icons.check),
                                    label: const Text('Onayla'),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: OutlinedButton.icon(
                                    onPressed: () => _reject(p),
                                    icon: const Icon(Icons.close),
                                    label: const Text('Reddet'),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
    );
  }
}
