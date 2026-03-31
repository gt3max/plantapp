import 'package:shared_preferences/shared_preferences.dart';
import 'package:plantapp/constants/api.dart';

/// Token storage using SharedPreferences (UserDefaults on iOS).
/// Survives app reinstalls — unlike Keychain which gets wiped.
class TokenService {
  TokenService._();
  static final instance = TokenService._();

  static const _accessTokenKey = 'access_token';
  static const _refreshTokenKey = 'refresh_token';
  static const _expiresKey = 'token_expires';
  static const _emailKey = 'user_email';

  Future<String?> getAccessToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_accessTokenKey);
  }

  Future<String?> getRefreshToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_refreshTokenKey);
  }

  Future<String?> getUserEmail() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_emailKey);
  }

  Future<int> getTokenExpires() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_expiresKey) ?? 0;
  }

  Future<bool> isTokenExpired() async {
    final expires = await getTokenExpires();
    return DateTime.now().millisecondsSinceEpoch >= expires - tokenRefreshBufferMs;
  }

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
    required int expiresIn,
    required String email,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final expiresAt = DateTime.now().millisecondsSinceEpoch + (expiresIn * 1000);
    await Future.wait([
      prefs.setString(_accessTokenKey, accessToken),
      prefs.setString(_refreshTokenKey, refreshToken),
      prefs.setInt(_expiresKey, expiresAt),
      prefs.setString(_emailKey, email),
    ]);
  }

  Future<void> updateAccessToken(String accessToken, int expiresIn) async {
    final prefs = await SharedPreferences.getInstance();
    final expiresAt = DateTime.now().millisecondsSinceEpoch + (expiresIn * 1000);
    await Future.wait([
      prefs.setString(_accessTokenKey, accessToken),
      prefs.setInt(_expiresKey, expiresAt),
    ]);
  }

  Future<void> clearAll() async {
    final prefs = await SharedPreferences.getInstance();
    await Future.wait([
      prefs.remove(_accessTokenKey),
      prefs.remove(_refreshTokenKey),
      prefs.remove(_expiresKey),
      prefs.remove(_emailKey),
    ]);
  }
}
