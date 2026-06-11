import 'package:flutter/material.dart';

class AppTheme {
  // SyncHabit mor paleti
  static const Color primary = Color(0xFF534AB7); // ana mor
  static const Color primaryDark = Color(0xFF3C3489); // koyu vurgu
  static const Color primaryLight = Color(0xFFEEEDFE); // açık arka plan/fill
  static const Color accent = Color(0xFF7F77DD); // orta ton (vurgu)

  static ThemeData get theme {
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primary,
        primary: primary,
        brightness: Brightness.light,
      ),
      scaffoldBackgroundColor: const Color(
        0xFFF7F7FB,
      ), // çok hafif gri-mor arka plan
    );

    return base.copyWith(
      // AppBar: mor zemin, beyaz yazı
      appBarTheme: const AppBarTheme(
        backgroundColor: primary,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: false,
      ),
      // Dolu butonlar (FilledButton)
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
        ),
      ),
      // Klasik ElevatedButton (varsa)
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
      ),
      // FAB (görev ekleme +)
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: primary,
        foregroundColor: Colors.white,
      ),
      // Alt navigasyon
      navigationBarTheme: NavigationBarThemeData(
        indicatorColor: primaryLight,
        backgroundColor: Colors.white,
        labelTextStyle: WidgetStateProperty.all(
          const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
        ),
      ),
      // Sekmeler (TabBar)
      tabBarTheme: const TabBarThemeData(
        labelColor: Colors.white,
        unselectedLabelColor: Color(0xCCFFFFFF),
        indicatorColor: Colors.white,
      ),
      // İlerleme çubuğu
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: primary,
        linearTrackColor: primaryLight,
      ),
      // Kartlar
      cardTheme: CardThemeData(
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: Colors.grey.shade200),
        ),
      ),
      // Chip (seviye rozeti vb.)
      chipTheme: ChipThemeData(
        backgroundColor: primaryLight,
        labelStyle: const TextStyle(
          color: primaryDark,
          fontWeight: FontWeight.w500,
        ),
        side: BorderSide.none,
      ),
      // Input alanları
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: primary, width: 2),
        ),
      ),
    );
  }
}
