/// API Gateway (AWS Lambda — EU Frankfurt)
const String apiBase =
    'https://p0833p2v29.execute-api.eu-central-1.amazonaws.com';

/// Auth endpoints (public)
class AuthEndpoints {
  AuthEndpoints._();

  static const login = '/auth/login';
  static const register = '/auth/register';
  static const verify = '/auth/verify';
  static const resendCode = '/auth/resend-code';
  static const refresh = '/auth/refresh';
  static const logout = '/auth/logout';
}

/// Plant endpoints (require JWT)
class PlantEndpoints {
  PlantEndpoints._();

  static const identify = '/plants/identify';
  static const care = '/plants/care';
  static const library = '/plants/library';
  static const save = '/plants/save';
}

/// Plant DB endpoints (public, Turso encyclopedia)
class PlantDBEndpoints {
  PlantDBEndpoints._();

  static const search = '/plants/db/search';
  static String detail(String id) => '/plants/db/$id';
  static const stats = '/plants/db/stats';
}

/// Device endpoints (require JWT + device_id)
class DeviceEndpoints {
  DeviceEndpoints._();

  static const list = '/devices';
  static String status(String id) => '/device/$id/status';
  static String water(String id) => '/device/$id/water';
  static String stop(String id) => '/device/$id/stop';
  static String config(String id) => '/device/$id/config';
  static String mode(String id) => '/device/$id/mode';
}

/// Token refresh buffer (5 minutes before expiry)
const int tokenRefreshBufferMs = 5 * 60 * 1000;
