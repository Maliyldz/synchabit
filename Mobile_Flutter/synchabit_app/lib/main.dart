import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/auth_provider.dart';
import 'screens/login_screen.dart';
import 'screens/main_shell.dart';
import 'providers/task_provider.dart';
import 'providers/group_provider.dart';
import 'config/app_theme.dart';
import 'services/profile_service.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

void main() {
  runApp(const SyncHabitApp());
}

class SyncHabitApp extends StatelessWidget {
  const SyncHabitApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => TaskProvider()),
        ChangeNotifierProvider(create: (_) => GroupProvider()),
      ],
      child: MaterialApp(
        title: 'SyncHabit',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.theme,
        locale: const Locale('tr'),
        supportedLocales: const [Locale('tr'), Locale('en')],
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        home: const _AuthGate(),
      ),
    );
  }
}

// Açılışta token'ı kontrol edip doğru ekrana yönlendirir
class _AuthGate extends StatefulWidget {
  const _AuthGate();

  @override
  State<_AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<_AuthGate> {
  bool _checking = true;
  bool _isLoggedIn = false;

  @override
  void initState() {
    super.initState();
    _checkToken();
  }

  Future<void> _checkToken() async {
    final auth = context.read<AuthProvider>();
    await auth.loadToken(); // kayıtlı token'ı yükle

    // Token yoksa direkt login
    if (auth.token == null) {
      if (!mounted) return;
      setState(() {
        _isLoggedIn = false;
        _checking = false;
      });
      return;
    }

    // Token var → geçerli mi diye backend'e sor (/api/auth/me)
    try {
      await ProfileService().fetchProfile(auth.token!);
      // Başarılı → token geçerli
      if (!mounted) return;
      setState(() {
        _isLoggedIn = true;
        _checking = false;
      });
    } catch (e) {
      // Hata (401 / süresi dolmuş / bağlantı) → token'ı temizle, login'e at
      await auth.logout();
      if (!mounted) return;
      setState(() {
        _isLoggedIn = false;
        _checking = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return _isLoggedIn ? const MainShell() : const LoginScreen();
  }
}
