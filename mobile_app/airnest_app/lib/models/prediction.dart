/// One day from /api/predictions.
class Prediction {
  final String date; // YYYY-MM-DD
  final double tempForecastC;
  final double tempLowC;
  final double tempHighC;
  final double humidityForecast;
  final int dangerPredicted; // 1 = danger, 0 = safe
  final String dangerLabel;
  final double dangerProbability; // 0..1
  final int isRainyForecast; // 1 = rainy
  final String? generatedAt;

  Prediction({
    required this.date,
    required this.tempForecastC,
    required this.tempLowC,
    required this.tempHighC,
    required this.humidityForecast,
    required this.dangerPredicted,
    required this.dangerLabel,
    required this.dangerProbability,
    required this.isRainyForecast,
    this.generatedAt,
  });

  static double _d(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }

  static int _i(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toInt();
    return int.tryParse(v.toString()) ?? 0;
  }

  factory Prediction.fromJson(Map<String, dynamic> j) => Prediction(
        date: (j['date'] ?? '').toString(),
        tempForecastC: _d(j['temp_forecast_c']),
        tempLowC: _d(j['temp_low_c']),
        tempHighC: _d(j['temp_high_c']),
        humidityForecast: _d(j['humidity_forecast']),
        dangerPredicted: _i(j['danger_predicted']),
        dangerLabel: (j['danger_label'] ?? '').toString(),
        dangerProbability: _d(j['danger_probability']),
        isRainyForecast: _i(j['is_rainy_forecast']),
        generatedAt: j['generated_at']?.toString(),
      );

  bool get isDanger => dangerPredicted == 1;
  bool get isRainy => isRainyForecast == 1;
  int get probPct => (dangerProbability * 100).round();
}

/// Dropdown options from /api/sensor-filters.
class FilterOptions {
  final List<String> years;
  final List<String> months;
  final List<String> days;
  final List<String> neighbourhoods;
  final List<String> cities;
  final List<String> countries;

  FilterOptions({
    required this.years,
    required this.months,
    required this.days,
    required this.neighbourhoods,
    required this.cities,
    required this.countries,
  });

  static List<String> _list(dynamic v) {
    if (v is List) {
      return v
          .where((e) => e != null && e.toString().isNotEmpty && e.toString() != 'empty')
          .map((e) => e.toString())
          .toList();
    }
    return [];
  }

  factory FilterOptions.fromJson(Map<String, dynamic> j) => FilterOptions(
        years: _list(j['years']),
        months: _list(j['months']),
        days: _list(j['days']),
        neighbourhoods: _list(j['neighbourhoods']),
        cities: _list(j['cities']),
        countries: _list(j['countries']),
      );
}
