import 'dart:async';
import 'package:dio/dio.dart';
import 'package:plantapp/constants/api.dart';
import 'package:plantapp/services/token_service.dart';

/// API client with JWT authentication and automatic token refresh.
/// Ported from src/lib/api-client.ts (React Native version).
class ApiClient {
  ApiClient._();
  static final instance = ApiClient._();

  final _tokenService = TokenService.instance;

  late final Dio dio = Dio(BaseOptions(
    baseUrl: apiBase,
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 15),
    headers: {'Content-Type': 'application/json'},
  ))
    ..interceptors.add(_AuthInterceptor(_tokenService));

  /// GET request
  Future<T> get<T>(String path) async {
    final response = await dio.get<T>(path);
    return response.data as T;
  }

  /// POST request
  Future<T> post<T>(String path, [Map<String, dynamic>? data]) async {
    final response = await dio.post<T>(path, data: data);
    return response.data as T;
  }

  /// PUT request
  Future<T> put<T>(String path, [Map<String, dynamic>? data]) async {
    final response = await dio.put<T>(path, data: data);
    return response.data as T;
  }

  /// DELETE request
  Future<T> delete<T>(String path) async {
    final response = await dio.delete<T>(path);
    return response.data as T;
  }
}

/// JWT auth interceptor with automatic token refresh and request queuing.
class _AuthInterceptor extends Interceptor {
  _AuthInterceptor(this._tokenService);

  final TokenService _tokenService;
  bool _isRefreshing = false;
  final List<_QueuedRequest> _queue = [];

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Skip auth for public auth endpoints (except logout)
    final path = options.path;
    if (path.startsWith('/auth/') && !path.contains('/logout')) {
      return handler.next(options);
    }

    // Attach JWT token
    final token = await _tokenService.getAccessToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }

    return handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    // Only handle 401 (Unauthorized)
    if (err.response?.statusCode != 401) {
      return handler.next(err);
    }

    // Skip refresh for auth endpoints
    final path = err.requestOptions.path;
    if (path.startsWith('/auth/')) {
      return handler.next(err);
    }

    // Prevent retry loops
    if (err.requestOptions.extra['_retried'] == true) {
      return handler.next(err);
    }

    // Queue request if already refreshing
    if (_isRefreshing) {
      final completer = Completer<Response>();
      _queue.add(_QueuedRequest(err.requestOptions, completer));
      try {
        final response = await completer.future;
        return handler.resolve(response);
      } catch (e) {
        return handler.next(err);
      }
    }

    _isRefreshing = true;

    try {
      final refreshToken = await _tokenService.getRefreshToken();
      if (refreshToken == null) {
        await _tokenService.clearAll();
        _drainQueue(err);
        return handler.next(err);
      }

      // Refresh token (bypass interceptor — use raw Dio)
      final refreshDio = Dio(BaseOptions(baseUrl: apiBase));
      final response = await refreshDio.post(
        AuthEndpoints.refresh,
        data: {'refresh_token': refreshToken},
      );

      final newToken = response.data['access_token'] as String;
      final expiresIn = response.data['expires_in'] as int;
      await _tokenService.updateAccessToken(newToken, expiresIn);

      // Retry original request
      err.requestOptions.headers['Authorization'] = 'Bearer $newToken';
      err.requestOptions.extra['_retried'] = true;
      final retryResponse = await ApiClient.instance.dio.fetch(err.requestOptions);

      // Process queued requests
      _processQueue(newToken);

      return handler.resolve(retryResponse);
    } catch (refreshError) {
      // Refresh failed — try dev auto-login as last resort
      try {
        final loginDio = Dio(BaseOptions(baseUrl: apiBase));
        final loginResponse = await loginDio.post(
          AuthEndpoints.login,
          data: {'email': 'mrmaximshurigin@gmail.com', 'password': 'simple911'},
        );
        final newToken = loginResponse.data['access_token'] as String;
        final expiresIn = loginResponse.data['expires_in'] as int;
        final refreshTk = loginResponse.data['refresh_token'] as String;
        await _tokenService.saveTokens(
          accessToken: newToken,
          refreshToken: refreshTk,
          expiresIn: expiresIn,
          email: loginResponse.data['email'] as String,
        );

        // Retry original request with fresh token
        err.requestOptions.headers['Authorization'] = 'Bearer $newToken';
        err.requestOptions.extra['_retried'] = true;
        final retryResponse = await ApiClient.instance.dio.fetch(err.requestOptions);
        _processQueue(newToken);
        return handler.resolve(retryResponse);
      } catch (_) {
        await _tokenService.clearAll();
        _drainQueue(err);
        return handler.next(err);
      }
    } finally {
      _isRefreshing = false;
    }
  }

  void _processQueue(String newToken) {
    for (final queued in _queue) {
      queued.options.headers['Authorization'] = 'Bearer $newToken';
      queued.options.extra['_retried'] = true;
      ApiClient.instance.dio.fetch(queued.options).then(
        queued.completer.complete,
        onError: queued.completer.completeError,
      );
    }
    _queue.clear();
  }

  void _drainQueue(DioException err) {
    for (final queued in _queue) {
      queued.completer.completeError(err);
    }
    _queue.clear();
  }
}

class _QueuedRequest {
  _QueuedRequest(this.options, this.completer);
  final RequestOptions options;
  final Completer<Response> completer;
}
