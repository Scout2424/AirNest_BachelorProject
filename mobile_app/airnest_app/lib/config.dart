/// App-wide configuration.
///
/// If your server's IP or port ever changes, this is the ONE place to edit.
/// The phone needs internet access to reach this address (it is a public
/// EC2 IP, so any Wi-Fi or mobile-data connection works — no same-network
/// requirement).
class Config {
  static const String apiBase = 'http://13.61.152.65:8080';
}
