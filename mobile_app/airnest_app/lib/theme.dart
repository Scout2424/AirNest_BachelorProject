import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Colours lifted directly from the website's style.css (:root variables and
/// the Chart.js COLORS object) so the app matches the site.
class AppColors {
  static const ink = Color(0xFF1E2A3A); // --ink
  static const muted = Color(0xFF6B7F96); // --muted
  static const accent = Color(0xFFB85C38); // --accent
  static const navBg = Color(0xFF4A7FA5); // --nav-bg (steel blue)
  static const navHover = Color(0xFF3D6D90); // --nav-hover-bg
  static const surface = Color(0xFFFFFFFF); // --surface

  // Background gradient (body in style.css, 160deg).
  static const bgGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFFB8E4E4),
      Color(0xFFCCE8DC),
      Color(0xFFDDD8CC),
      Color(0xFFC8DFF0),
      Color(0xFFA8D4EE),
    ],
    stops: [0.0, 0.20, 0.45, 0.70, 1.0],
  );

  // Header gradient (header in style.css, 135deg).
  static const headerGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFFE8F8F9),
      Color(0xFFD6F1F5),
      Color(0xFFC2EAF2),
      Color(0xFFAEE2EF),
    ],
  );

  // Per-sensor chart line colours (from the data page COLORS object).
  static const temp = Color(0xFFE07B54);
  static const hum = Color(0xFF4A7FA5);
  static const mq135 = Color(0xFF6DBF95);
  static const mq3 = Color(0xFFC97AB5);
  static const mq6 = Color(0xFFE0B854);
  static const mq7 = Color(0xFFE05454);
  static const mq8 = Color(0xFF54B8E0);
  static const soundV = Color(0xFF9B8FE0);
  static const soundE = Color(0xFFE09B54);

  // Prediction states.
  static const safe = Color(0xFF6DBF95);
  static const danger = Color(0xFFE05454);
}

/// Builds the global theme. Body text is Source Serif 4; headings use
/// Playfair Display, applied per-widget via [AppText].
ThemeData buildAppTheme() {
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(seedColor: AppColors.navBg),
    scaffoldBackgroundColor: Colors.transparent,
  );

  return base.copyWith(
    textTheme: GoogleFonts.sourceSerif4TextTheme(base.textTheme).apply(
      bodyColor: AppColors.ink,
      displayColor: AppColors.ink,
    ),
  );
}

/// Reusable text styles.
class AppText {
  static TextStyle heading(double size) => GoogleFonts.playfairDisplay(
        fontSize: size,
        fontWeight: FontWeight.w600,
        color: AppColors.ink,
      );

  static TextStyle body(double size, {Color? color, FontWeight? weight}) =>
      GoogleFonts.sourceSerif4(
        fontSize: size,
        color: color ?? AppColors.ink,
        fontWeight: weight ?? FontWeight.w400,
        height: 1.6,
      );
}
