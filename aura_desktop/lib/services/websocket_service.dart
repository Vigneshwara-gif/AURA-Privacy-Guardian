import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../core/constants/api_constants.dart';

enum WsConnectionStatus { connected, reconnecting, disconnected }

class WebSocketService {
  final String wsUrl;
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Timer? _reconnectTimer;
  Timer? _heartbeatTimer;

  WsConnectionStatus _status = WsConnectionStatus.disconnected;
  final _eventController = StreamController<Map<String, dynamic>>.broadcast();

  String? _sessionToken;
  int _retrySeconds = 2;

  WebSocketService({this.wsUrl = ApiConstants.defaultWsUrl});

  WsConnectionStatus get status => _status;
  Stream<Map<String, dynamic>> get eventStream => _eventController.stream;

  void setSessionToken(String? token) {
    _sessionToken = token;
  }

  void connect() {
    if (_status == WsConnectionStatus.connected) return;
    _cancelReconnect();

    final tokenParam = _sessionToken != null ? '?token=$_sessionToken' : '';
    final fullUrl = '$wsUrl$tokenParam';

    try {
      _channel = WebSocketChannel.connect(Uri.parse(fullUrl));
      _status = WsConnectionStatus.connected;

      _subscription = _channel!.stream.listen(
        (message) {
          try {
            final data = jsonDecode(message);
            if (data is Map<String, dynamic>) {
              _eventController.add(data);
            }
          } catch (e) {
            debugPrint('WebSocket message decode error: $e');
          }
        },
        onError: (error) {
          debugPrint('WebSocket stream error: $error');
          _handleDisconnect();
        },
        onDone: () {
          debugPrint('WebSocket stream closed.');
          _handleDisconnect();
        },
      );

      _startHeartbeat();
      _retrySeconds = 2;
    } catch (e) {
      debugPrint('WebSocket connection attempt failed: $e');
      _handleDisconnect();
    }
  }

  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 15), (_) {
      if (_status == WsConnectionStatus.connected) {
        try {
          _channel?.sink.add(jsonEncode({'type': 'PING', 'timestamp': DateTime.now().toIso8601String()}));
        } catch (_) {}
      }
    });
  }

  void _handleDisconnect() {
    _status = WsConnectionStatus.reconnecting;
    _subscription?.cancel();
    _heartbeatTimer?.cancel();
    _channel = null;

    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: _retrySeconds), () {
      debugPrint('Attempting WebSocket reconnect (retry in $_retrySeconds s)...');
      _retrySeconds = (_retrySeconds * 1.5).toInt().clamp(2, 30);
      connect();
    });
  }

  void _cancelReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  void disconnect() {
    _cancelReconnect();
    _heartbeatTimer?.cancel();
    _subscription?.cancel();
    _channel?.sink.close();
    _channel = null;
    _status = WsConnectionStatus.disconnected;
  }

  void dispose() {
    disconnect();
    _eventController.close();
  }
}
