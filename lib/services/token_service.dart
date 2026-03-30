import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:plantapp/constants/api.dart';

/// Secure token storage for JWT authentication.
/// Uses flutter_secure_storage (Keychain on iOS, EncryptedSharedPreferences on Android).
class TokenService {
  TokenService._();
  static final instance = TokenService._();

  final _storage = const FlutterSecureStorage();

  static const _accessTokenKey = 'access_token';
  static const _refreshTokenKey = 'refresh_token';
  static const _expiresKey = 'token_expires';
  static const _emailKey = 'user_email';

  Future<String?> getAccessToken() => _storage.read(key: _accessTokenKey);
  Future<String?> getRefreshToken() => _storage.read(key: _refreshTokenKey);
  Future<String?> getUserEmail() => _storage.read(key: _emailKey);

  Future<int> getTokenExpires() async {
    final raw = await _storage.read(key: _expiresKey);
    return raw != null ? int.tryParse(raw) ?? 0 : 0;
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
    final expiresAt = DateTime.now().millisecondsSinceEpoch + (expiresIn * 1000);
    await Future.wait([
      _storage.write(key: _accessTokenKey, value: accessToken),
      _storage.write(key: _refreshTokenKey, value: refreshToken),
      _storage.write(key: _expiresKey, value: expiresAt.toString()),
      _storage.write(key: _emailKey, value: email),
    ]);
  }

  Future<void> updateAccessToken(String accessToken, int expiresIn) async {
    final expiresAt = DateTime.now().millisecondsSinceEpoch + (expiresIn * 1000);
    await Future.wait([
      _storage.write(key: _accessTokenKey, value: accessToken),
      _storage.write(key: _expiresKey, value: expiresAt.toString()),
    ]);
  }

  Future<void> clearAll() async {
    await Future.wait([
      _storage.delete(key: _accessTokenKey),
      _storage.delete(key: _refreshTokenKey),
      _storage.delete(key: _expiresKey),
      _storage.delete(key: _emailKey),
    ]);
  }
}
