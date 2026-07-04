import 'dart:convert';
import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/sensor_reading.dart';
import '../models/prediction.dart';

/// Thin wrapper around the AirNest Flask API.
///
/// v1 only uses public endpoints (no login required), so there is no cookie /
/// session handling here yet.
class ApiService {
  static const _timeout = Duration(seconds: 15);

  Uri _uri(String path, [Map<String, String>? query]) {
    final base = Uri.parse(Config.apiBase);
    return base.replace(
      path: path,
      queryParameters: (query != null && query.isNotEmpty) ? query : null,
    );
  }

  /// GET /api/sensor-filters?year=&month=
  Future<FilterOptions> getFilters({String? year, String? month}) async {
    final q = <String, String>{};
    if (year != null && year.isNotEmpty) q['year'] = year;
    if (month != null && month.isNotEmpty) q['month'] = month;

    final res = await http.get(_uri('/api/sensor-filters', q)).timeout(_timeout);
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    if (data['success'] != true) {
      throw Exception('Failed to load filters');
    }
    return FilterOptions.fromJson(data);
  }

  /// GET /api/sensor-data?year=&month=&day=&neighbourhood=&city=&country=
  Future<List<SensorReading>> getSensorData({
    String? year,
    String? month,
    String? day,
    String? neighbourhood,
    String? city,
    String? country,
  }) async {
    final q = <String, String>{};
    void add(String k, String? v) {
      if (v != null && v.isNotEmpty) q[k] = v;
    }

    add('year', year);
    add('month', month);
    add('day', day);
    add('neighbourhood', neighbourhood);
    add('city', city);
    add('country', country);

    final res = await http.get(_uri('/api/sensor-data', q)).timeout(_timeout);
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    if (data['success'] != true) {
      throw Exception('Failed to load sensor data');
    }
    final list = (data['data'] as List?) ?? [];
    return list
        .map((e) => SensorReading.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// GET /api/predictions
  Future<List<Prediction>> getPredictions() async {
    final res = await http.get(_uri('/api/predictions')).timeout(_timeout);
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    if (data['success'] != true) {
      throw Exception('Failed to load predictions');
    }
    final list = (data['predictions'] as List?) ?? [];
    return list
        .map((e) => Prediction.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// POST /api/contact
  Future<bool> sendContact({
    required String name,
    required String email,
    required String subject,
    required String message,
  }) async {
    final res = await http
        .post(
          _uri('/api/contact'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'name': name,
            'email': email,
            'subject': subject,
            'message': message,
          }),
        )
        .timeout(_timeout);
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    return data['success'] == true;
  }
}
