import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../models/prediction.dart';
import '../theme.dart';
import '../widgets/common.dart';

class PredictionsScreen extends StatefulWidget {
  const PredictionsScreen({super.key});
  @override
  State<PredictionsScreen> createState() => _PredictionsScreenState();
}

class _PredictionsScreenState extends State<PredictionsScreen> {
  final _api = ApiService();
  List<Prediction> _preds = [];
  String _status = 'Loading forecast…';
  String _title = 'Forecast';
  bool _loading = true;

  static const _dayNames = [
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
  ];
  static const _monthNames = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _status = 'Loading forecast…';
    });
    try {
      final preds = await _api.getPredictions();
      final dayCount = preds.length;
      setState(() {
        _preds = preds;
        _loading = false;
        _status = preds.isEmpty
            ? 'No forecast available yet — the station will generate one at 7 AM.'
            : '';
        _title = preds.isEmpty ? 'Forecast' : '$dayCount-Day Forecast';
      });
    } catch (_) {
      setState(() {
        _loading = false;
        _status = 'Could not load predictions. Please try again later.';
      });
    }
  }

  ({String day, String date}) _fmt(String dateStr) {
    try {
      final parts = dateStr.split('-').map(int.parse).toList();
      final dt = DateTime(parts[0], parts[1], parts[2]);
      return (
        day: _dayNames[dt.weekday - 1],
        date: '${parts[2]} ${_monthNames[parts[1] - 1]} ${parts[0]}',
      );
    } catch (_) {
      return (day: '', date: dateStr);
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
        children: [
           PageTitle(_title),
          const SizedBox(height: 12),
          SurfaceCard(
            padding: const EdgeInsets.all(14),
            child: Text(
              'Predictions are generated automatically every day at 7:00 AM by '
              'the Raspberry Pi station. Each run generates a 7-day prediction.',
              style: AppText.body(13, color: AppColors.muted),
            ),
          ),
          const SizedBox(height: 16),
          if (_status.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: Center(
                child: _loading
                    ? const CircularProgressIndicator()
                    : Text(_status,
                        textAlign: TextAlign.center,
                        style: AppText.body(14, color: AppColors.muted)),
              ),
            ),
          ..._preds.asMap().entries.map((e) => _card(e.value, e.key == 0)),
          if (_preds.isNotEmpty && _preds.first.generatedAt != null) ...[
            const SizedBox(height: 6),
            Text(
              _preds.length < 7
                  ? 'Last updated: ${_preds.first.generatedAt} · Showing ${_preds.length} of up to 7 days — the station hasn\'t generated newer predictions yet.'
                  : 'Last updated: ${_preds.first.generatedAt}',
              style: AppText.body(12, color: AppColors.muted),
            ),
          ],
        ],
      ),
    );
  }

  Widget _card(Prediction p, bool isToday) {
    final f = _fmt(p.date);
    final stateColor = p.isDanger ? AppColors.danger : AppColors.safe;
    final barWidth = (p.probPct.clamp(0, 100)) / 100.0;

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.94),
        borderRadius: BorderRadius.circular(14),
        border: Border(left: BorderSide(color: stateColor, width: 5)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.06),
            blurRadius: 12,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(f.day, style: AppText.heading(18)),
                      if (isToday) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppColors.navBg.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text('Today',
                              style: AppText.body(11, color: AppColors.navBg)),
                        ),
                      ],
                    ],
                  ),
                  Text(f.date,
                      style: AppText.body(13, color: AppColors.muted)),
                ],
              ),
              Text(p.isRainy ? '🌧' : '☀️',
                  style: const TextStyle(fontSize: 28)),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text('${p.tempForecastC.toStringAsFixed(1)}°C',
                  style: AppText.heading(26)),
              const SizedBox(width: 10),
              Text(
                '${p.tempLowC.toStringAsFixed(0)}° – ${p.tempHighC.toStringAsFixed(0)}°',
                style: AppText.body(14, color: AppColors.muted),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text('💧 ${p.humidityForecast.toStringAsFixed(0)}% humidity',
              style: AppText.body(14, color: AppColors.muted)),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: stateColor.withOpacity(0.14),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              p.isDanger ? '⚠ DANGER' : '✓ SAFE',
              style: AppText.body(13, color: stateColor, weight: FontWeight.w600),
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: LinearProgressIndicator(
                    value: barWidth,
                    minHeight: 8,
                    backgroundColor: Colors.black.withOpacity(0.07),
                    valueColor: AlwaysStoppedAnimation(stateColor),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Text('${p.probPct}% risk',
                  style: AppText.body(12, color: AppColors.muted)),
            ],
          ),
        ],
      ),
    );
  }
}
