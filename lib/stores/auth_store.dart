import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:plantapp/constants/api.dart';
import 'package:plantapp/models/auth.dart';
import 'package:plantapp/services/api_client.dart';
import 'package:plantapp/services/token_service.dart';

/// Auth state
enum AuthStatus { loading, authenticated, unauthenticated }

class AuthState {
  final AuthStatus status;
  final String? email;
  final String? error;
  final String? pendingEmail; // email waiting for verification

  const AuthState({
    this.status = AuthStatus.loading,
    this.email,
    this.error,
    this.pendingEmail,
  });

  AuthState copyWith({
    AuthStatus? status,
    String? email,
    String? error,
    String? pendingEmail,
  }) =>
      AuthState(
        status: status ?? this.status,
        email: email ?? this.email,
        error: error,
        pendingEmail: pendingEmail ?? this.pendingEmail,
      );
}

/// Auth state notifier — handles login, register, verify, logout.
/// Ported from src/stores/auth-store.ts
class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(const AuthState());

  final _api = ApiClient.instance;
  final _tokenService = TokenService.instance;

  // Dev auto-login credentials (remove before App Store release)
  static const _devEmail = 'mrmaximshurigin@gmail.com';
  static const _devPassword = 'simple911';

  /// Initialize auth state from stored tokens, with dev auto-login fallback
  Future<void> initialize() async {
    try {
      final token = await _tokenService.getAccessToken();
      final expired = await _tokenService.isTokenExpired();
      final email = await _tokenService.getUserEmail();

      if (token != null && !expired) {
        state = AuthState(
          status: AuthStatus.authenticated,
          email: email,
        );
        return;
      }

      if (token != null && expired) {
        // Try refresh
        final refreshToken = await _tokenService.getRefreshToken();
        if (refreshToken != null) {
          try {
            final data = await _api.post<Map<String, dynamic>>(
              AuthEndpoints.refresh,
              {'refresh_token': refreshToken},
            );
            await _tokenService.updateAccessToken(
              data['access_token'] as String,
              data['expires_in'] as int,
            );
            state = AuthState(
              status: AuthStatus.authenticated,
              email: email,
            );
            return;
          } catch (_) {
            // Refresh failed, fall through to dev auto-login
          }
        }
      }

      // Dev auto-login: no valid token → login automatically
      await _devAutoLogin();
    } catch (_) {
      // Last resort: try dev auto-login
      try {
        await _devAutoLogin();
      } catch (_) {
        state = const AuthState(status: AuthStatus.unauthenticated);
      }
    }
  }

  Future<void> _devAutoLogin() async {
    try {
      final data = await _api.post<Map<String, dynamic>>(
        AuthEndpoints.login,
        {'email': _devEmail, 'password': _devPassword},
      );
      final auth = AuthResponse.fromJson(data);
      await _tokenService.saveTokens(
        accessToken: auth.accessToken,
        refreshToken: auth.refreshToken,
        expiresIn: auth.expiresIn,
        email: auth.email,
      );
      state = AuthState(
        status: AuthStatus.authenticated,
        email: auth.email,
      );
    } catch (e) {
      await _tokenService.clearAll();
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  /// Login with email and password
  Future<void> login(LoginRequest req) async {
    state = state.copyWith(status: AuthStatus.loading, error: null);
    try {
      final data = await _api.post<Map<String, dynamic>>(
        AuthEndpoints.login,
        req.toJson(),
      );
      final auth = AuthResponse.fromJson(data);
      await _tokenService.saveTokens(
        accessToken: auth.accessToken,
        refreshToken: auth.refreshToken,
        expiresIn: auth.expiresIn,
        email: auth.email,
      );
      state = AuthState(
        status: AuthStatus.authenticated,
        email: auth.email,
      );
    } catch (e) {
      final message = _extractError(e, 'Login failed');
      if (message.toLowerCase().contains('not verified') ||
          message.toLowerCase().contains('verify')) {
        state = AuthState(
          status: AuthStatus.unauthenticated,
          error: message,
          pendingEmail: req.email,
        );
      } else {
        state = AuthState(
          status: AuthStatus.unauthenticated,
          error: message,
        );
      }
    }
  }

  /// Register new account
  Future<void> register(RegisterRequest req) async {
    state = state.copyWith(status: AuthStatus.loading, error: null);
    try {
      await _api.post<Map<String, dynamic>>(
        AuthEndpoints.register,
        req.toJson(),
      );
      state = AuthState(
        status: AuthStatus.unauthenticated,
        pendingEmail: req.email,
      );
    } catch (e) {
      state = AuthState(
        status: AuthStatus.unauthenticated,
        error: _extractError(e, 'Registration failed'),
      );
    }
  }

  /// Verify email with code
  Future<void> verify(VerifyRequest req) async {
    state = state.copyWith(status: AuthStatus.loading, error: null);
    try {
      final data = await _api.post<Map<String, dynamic>>(
        AuthEndpoints.verify,
        req.toJson(),
      );
      final auth = AuthResponse.fromJson(data);
      await _tokenService.saveTokens(
        accessToken: auth.accessToken,
        refreshToken: auth.refreshToken,
        expiresIn: auth.expiresIn,
        email: auth.email,
      );
      state = AuthState(
        status: AuthStatus.authenticated,
        email: auth.email,
      );
    } catch (e) {
      state = AuthState(
        status: AuthStatus.unauthenticated,
        error: _extractError(e, 'Verification failed'),
        pendingEmail: state.pendingEmail,
      );
    }
  }

  /// Resend verification code
  Future<void> resendCode() async {
    final email = state.pendingEmail;
    if (email == null) return;
    state = state.copyWith(error: null);
    try {
      await _api.post<Map<String, dynamic>>(
        AuthEndpoints.resendCode,
        {'email': email},
      );
    } catch (e) {
      state = state.copyWith(
        error: _extractError(e, 'Failed to resend code'),
      );
    }
  }

  /// Logout
  Future<void> logout() async {
    try {
      await _api.post<Map<String, dynamic>>(AuthEndpoints.logout);
    } catch (_) {
      // Ignore logout API errors
    }
    await _tokenService.clearAll();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }

  String _extractError(dynamic err, String fallback) {
    if (err is DioException) {
      final data = err.response?.data;
      if (data is Map) {
        return (data['error'] ?? data['message'] ?? fallback) as String;
      }
    }
    if (err is Error) return err.toString();
    return fallback;
  }
}

/// Riverpod provider
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier();
});
