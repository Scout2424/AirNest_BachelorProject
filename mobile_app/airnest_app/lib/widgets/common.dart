import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme.dart';

/// Two-tone "AirNest" wordmark (Air in ink, Nest in steel blue), as on the site.
class AirNestWordmark extends StatelessWidget {
  final double size;
  const AirNestWordmark({super.key, this.size = 22});

  @override
  Widget build(BuildContext context) {
    return RichText(
      text: TextSpan(
        style: GoogleFonts.playfairDisplay(
          fontSize: size,
          fontWeight: FontWeight.w600,
        ),
        children: const [
          TextSpan(text: 'Air', style: TextStyle(color: AppColors.ink)),
          TextSpan(text: 'Nest', style: TextStyle(color: AppColors.navBg)),
        ],
      ),
    );
  }
}

/// A gradient AppBar carrying the wordmark, used on every screen.
PreferredSizeWidget airNestAppBar() {
  return AppBar(
    elevation: 0,
    scrolledUnderElevation: 0,
    backgroundColor: Colors.transparent,
    flexibleSpace: Container(
      decoration: const BoxDecoration(
        gradient: AppColors.headerGradient,
        border: Border(bottom: BorderSide(color: Color(0xFF9DD5E8))),
      ),
    ),
    title: const AirNestWordmark(),
    centerTitle: false,
  );
}

/// White rounded card used to group content (matches the site's surfaces).
class SurfaceCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry margin;
  const SurfaceCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(18),
    this.margin = EdgeInsets.zero,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: margin,
      padding: padding,
      decoration: BoxDecoration(
        color: AppColors.surface.withOpacity(0.92),
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.06),
            blurRadius: 14,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: child,
    );
  }
}

/// Page heading (Playfair Display), matching .page-title.
class PageTitle extends StatelessWidget {
  final String text;
  const PageTitle(this.text, {super.key});
  @override
  Widget build(BuildContext context) =>
      Text(text, style: AppText.heading(26));
}
