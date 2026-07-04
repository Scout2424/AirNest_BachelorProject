import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../models/sensor_reading.dart';
import '../models/prediction.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/sensor_chart.dart';

class DataScreen extends StatefulWidget {
  const DataScreen({super.key});
  @override
  State<DataScreen> createState() => _DataScreenState();
}

class _DataScreenState extends State<DataScreen> {
  final _api = ApiService();

  FilterOptions? _opt;
  String? _year, _month, _day, _neighbourhood, _city, _country;

  List<SensorReading> _rows = [];
  String _status = 'Loading data…';
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    await _loadFilters(null);
    await _loadData();
  }

  Future<void> _loadFilters(String? changed) async {
    try {
      final opt = await _api.getFilters(year: _year, month: _month);
      setState(() {
        _opt = opt;
        if (_year != null && !opt.years.contains(_year)) _year = null;
        if (changed == 'year') {
          _month = null;
        } else if (_month != null && !opt.months.contains(_month)) {
          _month = null;
        }
        // Days always reset when the year/month context changes.
        _day = null;
        if (changed != null) {
          if (_neighbourhood != null &&
              !opt.neighbourhoods.contains(_neighbourhood)) {
            _neighbourhood = null;
          }
          if (_city != null && !opt.cities.contains(_city)) _city = null;
          if (_country != null && !opt.countries.contains(_country)) {
            _country = null;
          }
        }
      });
    } catch (_) {
      // leave existing options in place on failure
    }
  }

  Future<void> _loadData() async {
    setState(() {
      _loading = true;
      _status = 'Loading…';
    });
    try {
      final rows = await _api.getSensorData(
        year: _year,
        month: _month,
        day: _day,
        neighbourhood: _neighbourhood,
        city: _city,
        country: _country,
      );
      setState(() {
        _rows = rows;
        _loading = false;
        _status = rows.isEmpty ? 'No data found for the selected filters.' : '';
      });
    } catch (_) {
      setState(() {
        _loading = false;
        _status = 'Could not reach the server. Is the station online?';
      });
    }
  }

  void _reset() {
    setState(() {
      _year = _month = _day = null;
      _neighbourhood = _city = _country = null;
    });
    _loadFilters(null).then((_) => _loadData());
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
      children: [
        const PageTitle('Sensor Data'),
        const SizedBox(height: 16),
        _filtersCard(),
        const SizedBox(height: 16),
        if (_status.isNotEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 24),
            child: Center(
              child: _loading
                  ? const CircularProgressIndicator()
                  : Text(_status,
                      style: AppText.body(14, color: AppColors.muted)),
            ),
          ),
        if (_status.isEmpty) ..._charts(),
      ],
    );
  }

  Widget _filtersCard() {
    final opt = _opt;
    return SurfaceCard(
      child: LayoutBuilder(builder: (context, c) {
        final w = (c.maxWidth - 12) / 2;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Time',
                style: AppText.body(12,
                    color: AppColors.muted, weight: FontWeight.w600)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                _dropdown(w, 'Year', _year, opt?.years ?? [], 'All', (v) {
                  setState(() {
                    _year = v;
                    _month = null;
                    _day = null;
                  });
                  _loadFilters('year');
                }),
                _dropdown(w, 'Month', _month, opt?.months ?? [], 'All', (v) {
                  setState(() {
                    _month = v;
                    _day = null;
                  });
                  _loadFilters('month');
                }),
                _dropdown(w, 'Day', _day, opt?.days ?? [], 'All',
                    (v) => setState(() => _day = v)),
              ],
            ),
            const SizedBox(height: 16),
            Text('Location',
                style: AppText.body(12,
                    color: AppColors.muted, weight: FontWeight.w600)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                _dropdown(w, 'Neighbourhood', _neighbourhood,
                    opt?.neighbourhoods ?? [], 'None',
                    (v) => setState(() => _neighbourhood = v)),
                _dropdown(w, 'City', _city, opt?.cities ?? [], 'All',
                    (v) => setState(() => _city = v)),
                _dropdown(w, 'Country', _country, opt?.countries ?? [], 'All',
                    (v) => setState(() => _country = v)),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: AppColors.navBg),
                    onPressed: _loadData,
                    child: const Text('Apply'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.muted),
                    onPressed: _reset,
                    child: const Text('Reset All'),
                  ),
                ),
              ],
            ),
          ],
        );
      }),
    );
  }

  Widget _dropdown(double width, String label, String? value,
      List<String> items, String leading, ValueChanged<String?> onChanged) {
    // Guard: value must exist in items or be null.
    final safeValue = (value != null && items.contains(value)) ? value : null;
    return SizedBox(
      width: width,
      child: DropdownButtonFormField<String?>(
        value: safeValue,
        isExpanded: true,
        isDense: true,
        decoration: InputDecoration(
          labelText: label,
          labelStyle: AppText.body(12, color: AppColors.muted),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
          border:
              OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          filled: true,
          fillColor: Colors.white,
        ),
        style: AppText.body(13),
        items: [
          DropdownMenuItem<String?>(value: null, child: Text(leading)),
          ...items.map((e) =>
              DropdownMenuItem<String?>(value: e, child: Text(e))),
        ],
        onChanged: onChanged,
      ),
    );
  }

  List<Widget> _charts() {
    final labels = _rows.map((r) => r.time).toList();
    List<double?> col(double? Function(SensorReading) f) =>
        _rows.map(f).toList();

    return [
      SensorLineChart(
        title: 'Temperature',
        unit: '°C',
        labels: labels,
        values: col((r) => r.temperatureC),
        color: AppColors.temp,
      ),
      SensorLineChart(
        title: 'Humidity',
        unit: '%',
        labels: labels,
        values: col((r) => r.humidity),
        color: AppColors.hum,
      ),
      SensorLineChart(
        title: 'MQ-135 — eCO\u2082',
        unit: 'ppm',
        labels: labels,
        values: col((r) => r.mq135),
        color: AppColors.mq135,
        hardCap: 10000,
      ),
      SensorLineChart(
        title: 'MQ-3 — Alcohol / Benzene',
        unit: 'ppm',
        labels: labels,
        values: col((r) => r.mq3),
        color: AppColors.mq3,
        hardCap: 500,
      ),
      SensorLineChart(
        title: 'MQ-6 — LPG / Butane',
        unit: 'ppm',
        labels: labels,
        values: col((r) => r.mq6),
        color: AppColors.mq6,
        hardCap: 10000,
      ),
      SensorLineChart(
        title: 'MQ-7 — Carbon Monoxide',
        unit: 'ppm',
        labels: labels,
        values: col((r) => r.mq7),
        color: AppColors.mq7,
        hardCap: 2000,
      ),
      SensorLineChart(
        title: 'MQ-8 — Hydrogen',
        unit: 'ppm',
        labels: labels,
        values: col((r) => r.mq8),
        color: AppColors.mq8,
        hardCap: 10000,
      ),
      SensorLineChart(
        title: 'Sound — Background voltage',
        unit: 'V',
        labels: labels,
        values: col((r) => r.soundV),
        color: AppColors.soundV,
      ),
      SensorLineChart(
        title: 'Sound — Events per 30-min session',
        unit: 'events',
        labels: labels,
        values: col((r) => r.soundEvents),
        color: AppColors.soundE,
      ),
    ];
  }
}
