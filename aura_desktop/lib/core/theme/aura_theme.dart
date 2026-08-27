import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AuraTheme {
  // Deep Cybersecurity Dark Palette
  static const Color background = Color(0xFF0B0F19);      // Deep Midnight Void
  static const Color surface = Color(0xFF121826);         // Slate Container
  static const Color surfaceElevated = Color(0xFF1A2234); // Elevated Container
  static const Color surfaceHighlight = Color(0xFF222D42);// Highlight Container

  static const Color border = Color(0xFF1E293B);          // Subtle Border
  static const Color borderSubtle = Color(0xFF151E2E);    // Faint Border
  static const Color borderHighlight = Color(0xFF38BDF8); // Cyan Accent Border

  // Brand Accents
  static const Color primary = Color(0xFF0284C7);        // Electric Cobalt Blue
  static const Color primaryLight = Color(0xFF38BDF8);   // Neon Cyan
  static const Color accentTeal = Color(0xFF14B8A6);     // Emerald Teal Sentinel
  static const Color accentIndigo = Color(0xFF6366F1);   // Deep Intelligence Indigo

  // Status & Severity Colors
  static const Color critical = Color(0xFFEF4444);       // Red Alert
  static const Color high = Color(0xFFF97316);           // Orange Alert
  static const Color medium = Color(0xFFFBBF24);         // Amber Warning
  static const Color warning = Color(0xFFFBBF24);        // Warning Amber
  static const Color low = Color(0xFF38BDF8);            // Info Blue
  static const Color info = Color(0xFF94A3B8);           // Neutral Slate
  static const Color healthy = Color(0xFF10B981);        // Success Green

  // Typography
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: background,
      primaryColor: primary,
      cardColor: surface,
      dividerColor: border,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        secondary: primaryLight,
        surface: surface,
        error: critical,
      ),
      textTheme: GoogleFonts.interTextTheme(
        ThemeData.dark().textTheme,
      ).apply(
        bodyColor: textPrimary,
        displayColor: textPrimary,
      ),
      scrollbarTheme: ScrollbarThemeData(
        thumbColor: WidgetStateProperty.all(const Color(0xFF334155)),
        trackColor: WidgetStateProperty.all(Colors.transparent),
        radius: const Radius.circular(4),
      ),
    );
  }

  static Color getSeverityColor(String? severity) {
    if (severity == null) return textSecondary;
    switch (severity.toUpperCase().trim()) {
      case 'CRITICAL':
      case 'FAIL':
      case 'FAILED':
        return critical;
      case 'HIGH':
        return high;
      case 'MEDIUM':
      case 'WARN':
      case 'WARNING':
      case 'ELEVATED':
      case 'ATTENTION':
        return warning;
      case 'LOW':
        return low;
      case 'NORMAL':
      case 'INFO':
      case 'INFORMATIONAL':
      case 'HEALTHY':
      case 'NOMINAL':
      case 'PASS':
      case 'PASSED':
      case 'OK':
      case 'PROTECTED':
        return healthy;
      default:
        return textSecondary;
    }
  }
}
