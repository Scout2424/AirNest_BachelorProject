import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../theme.dart';

/// A single sensor line chart, styled to match the website's Chart.js charts.
///
/// [values] is parallel to [labels]; null entries are gaps (no point drawn),
/// exactly like the web version skipping 'N/A' / null.
class SensorLineChart extends StatelessWidget {
  final String title;
  final String unit;
  final List<String> labels; // time strings "HH:MM:SS"
  final List<double?> values;
  final Color color;

  /// Hard display cap (e.g. 10000 ppm). Pass null for auto (temp / humidity).
  final double? hardCap;

  const SensorLineChart({
    super.key,
    required this.title,
    required this.unit,
    required this.labels,
    required this.values,
    required this.color,
    this.hardCap,
  });

  double _maxY() {
    final valid = values.whereType<double>().toList();
    final dataMax = valid.isEmpty ? 0.0 : valid.reduce(math.max);
    if (hardCap == null) {
      final m = (dataMax * 1.15).ceilToDouble();
      return m <= 0 ? 1 : m;
    }
    final suggested = dataMax <= hardCap!
        ? math.min(hardCap!, (dataMax * 1.15).ceilToDouble())
        : hardCap!;
    return suggested <= 0 ? hardCap! : suggested;
  }

  @override
  Widget build(BuildContext context) {
    final spots = <FlSpot>[];
    for (var i = 0; i < values.length; i++) {
      final v = values[i];
      if (v != null && !v.isNaN) spots.add(FlSpot(i.toDouble(), v));
    }

    final maxY = _maxY();
    final n = labels.length;
    final step = (n / 6).ceil().clamp(1, 100000).toInt();
    final maxX = n > 1 ? (n - 1).toDouble() : 1.0;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.fromLTRB(14, 14, 16, 10),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.92),
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.06),
            blurRadius: 12,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Text(title,
                    style: AppText.body(14, weight: FontWeight.w600)),
              ),
              Text(unit, style: AppText.body(11, color: AppColors.muted)),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 190,
            child: spots.isEmpty
                ? Center(
                    child: Text('No data',
                        style: AppText.body(12, color: AppColors.muted)),
                  )
                : LineChart(
                    LineChartData(
                      minX: 0,
                      maxX: maxX,
                      minY: 0,
                      maxY: maxY,
                      clipData: FlClipData.all(),
                      gridData: FlGridData(
                        show: true,
                        drawVerticalLine: false,
                        getDrawingHorizontalLine: (_) => FlLine(
                          color: Colors.black.withOpacity(0.05),
                          strokeWidth: 1,
                        ),
                      ),
                      borderData: FlBorderData(show: false),
                      titlesData: FlTitlesData(
                        topTitles: const AxisTitles(
                            sideTitles: SideTitles(showTitles: false)),
                        rightTitles: const AxisTitles(
                            sideTitles: SideTitles(showTitles: false)),
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 44,
                            getTitlesWidget: (value, meta) => Text(
                              _fmtY(value),
                              style: AppText.body(9, color: AppColors.muted),
                            ),
                          ),
                        ),
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 26,
                            interval: 1,
                            getTitlesWidget: (value, meta) {
                              final i = value.round();
                              if (i < 0 || i >= n) return const SizedBox();
                              if (i % step != 0) return const SizedBox();
                              final t = labels[i];
                              final short =
                                  t.length >= 5 ? t.substring(0, 5) : t;
                              return Padding(
                                padding: const EdgeInsets.only(top: 6),
                                child: Text(short,
                                    style: AppText.body(9,
                                        color: AppColors.muted)),
                              );
                            },
                          ),
                        ),
                      ),
                      lineTouchData: LineTouchData(
                        touchTooltipData: LineTouchTooltipData(
                          getTooltipColor: (_) => AppColors.ink,
                          getTooltipItems: (touched) => touched.map((s) {
                            final i = s.x.round();
                            final label =
                                (i >= 0 && i < n) ? labels[i] : '';
                            return LineTooltipItem(
                              '$label\n${s.y.toStringAsFixed(1)} $unit',
                              const TextStyle(
                                  color: Colors.white, fontSize: 11),
                            );
                          }).toList(),
                        ),
                      ),
                      lineBarsData: [
                        LineChartBarData(
                          spots: spots,
                          isCurved: true,
                          curveSmoothness: 0.35,
                          color: color,
                          barWidth: 2,
                          dotData: FlDotData(show: spots.length <= 100),
                          belowBarData: BarAreaData(
                            show: true,
                            color: color.withOpacity(0.12),
                          ),
                        ),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  String _fmtY(double v) {
    if (v >= 1000) return '${(v / 1000).toStringAsFixed(v % 1000 == 0 ? 0 : 1)}k';
    if (v == v.roundToDouble()) return v.toStringAsFixed(0);
    return v.toStringAsFixed(1);
  }
}
