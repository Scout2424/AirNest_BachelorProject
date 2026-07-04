import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'theme.dart';
import 'widgets/common.dart';
import 'screens/home_screen.dart';
import 'screens/data_screen.dart';
import 'screens/predictions_screen.dart';
import 'screens/contact_screen.dart';

void main() {
  GoogleFonts.config.allowRuntimeFetching = false;
  runApp(const AirNestApp());
}

class AirNestApp extends StatelessWidget {
  const AirNestApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AirNest',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      home: const RootShell(),
    );
  }
}

class RootShell extends StatefulWidget {
  const RootShell({super.key});
  @override
  State<RootShell> createState() => _RootShellState();
}

class _RootShellState extends State<RootShell> {
  int _index = 0;

  // Keep each tab's state alive when switching tabs.
  final _screens = const [
    HomeScreen(),
    DataScreen(),
    PredictionsScreen(),
    ContactScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(gradient: AppColors.bgGradient),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: airNestAppBar(),
        body: SafeArea(
          child: IndexedStack(index: _index, children: _screens),
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (i) => setState(() => _index = i),
          backgroundColor: Colors.white.withOpacity(0.95),
          indicatorColor: AppColors.navBg.withOpacity(0.15),
          destinations: const [
            NavigationDestination(
                icon: Icon(Icons.home_outlined),
                selectedIcon: Icon(Icons.home, color: AppColors.navBg),
                label: 'Home'),
            NavigationDestination(
                icon: Icon(Icons.bar_chart_outlined),
                selectedIcon: Icon(Icons.bar_chart, color: AppColors.navBg),
                label: 'Data'),
            NavigationDestination(
                icon: Icon(Icons.auto_graph_outlined),
                selectedIcon: Icon(Icons.auto_graph, color: AppColors.navBg),
                label: 'Predictions'),
            NavigationDestination(
                icon: Icon(Icons.mail_outline),
                selectedIcon: Icon(Icons.mail, color: AppColors.navBg),
                label: 'Contact'),
          ],
        ),
      ),
    );
  }
}