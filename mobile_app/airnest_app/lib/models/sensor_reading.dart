/// One row from /api/sensor-data.
class SensorReading {
  final String time;
  final double? temperatureC;
  final double? humidity;
  final double? mq135;
  final double? mq3;
  final double? mq6;
  final double? mq7;
  final double? mq8;
  final double? soundV;
  final double? soundEvents;

  SensorReading({
    required this.time,
    this.temperatureC,
    this.humidity,
    this.mq135,
    this.mq3,
    this.mq6,
    this.mq7,
    this.mq8,
    this.soundV,
    this.soundEvents,
  });

  /// Mirrors the website's parsing: 'N/A' or null -> null, otherwise a double.
  static double? _d(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    final s = v.toString();
    if (s == 'N/A' || s.isEmpty) return null;
    return double.tryParse(s);
  }

  factory SensorReading.fromJson(Map<String, dynamic> j) => SensorReading(
        time: (j['time'] ?? '').toString(),
        temperatureC: _d(j['temperature_c']),
        humidity: _d(j['humidity']),
        mq135: _d(j['mq135_ppm']),
        mq3: _d(j['mq3_ppm']),
        mq6: _d(j['mq6_ppm']),
        mq7: _d(j['mq7_ppm']),
        mq8: _d(j['mq8_ppm']),
        soundV: _d(j['sound_v']),
        soundEvents: _d(j['sound_events']),
      );
}
