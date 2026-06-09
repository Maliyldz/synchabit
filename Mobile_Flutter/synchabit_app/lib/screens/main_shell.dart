import 'package:flutter/material.dart';
import 'home_screen.dart';
import 'groups_screen.dart';
import 'friends_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _selectedIndex = 0;

  // Her sekmenin ekranı. Görevlerim ve Gruplarım gerçek;
  // Arkadaşlarım ve Profil şimdilik placeholder.
  final List<Widget> _screens = const [
    HomeScreen(),
    GroupsScreen(),
    FriendsScreen(),
    _PlaceholderScreen(
      title: 'Arkadaşlarım',
      message: 'Bu özellik yakında eklenecek.',
    ),
    _PlaceholderScreen(
      title: 'Profil',
      message: 'Bu özellik yakında eklenecek.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_selectedIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          setState(() => _selectedIndex = index);
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.check_circle_outline),
            selectedIcon: Icon(Icons.check_circle),
            label: 'Görevlerim',
          ),
          NavigationDestination(
            icon: Icon(Icons.groups_outlined),
            selectedIcon: Icon(Icons.groups),
            label: 'Gruplarım',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outline),
            selectedIcon: Icon(Icons.people),
            label: 'Arkadaşlarım',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profil',
          ),
        ],
      ),
    );
  }
}

// Henüz yapılmamış sekmeler için basit "yakında" ekranı
class _PlaceholderScreen extends StatelessWidget {
  final String title;
  final String message;
  const _PlaceholderScreen({required this.title, required this.message});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(message, textAlign: TextAlign.center),
        ),
      ),
    );
  }
}
