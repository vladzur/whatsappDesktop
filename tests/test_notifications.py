"""Tests para el NotificationManager."""

from unittest.mock import MagicMock, patch
import whatsapp_desk.notifications as notif_module


@patch("whatsapp_desk.notifications.Notify")
@patch("whatsapp_desk.notifications.WebKit")
def test_notification_manager_registers_handler(mock_webkit, mock_notify):
    """Debe registrar el script message handler en WebKit."""
    notif_module.NOTIFY_AVAILABLE = True

    mock_webview = MagicMock()
    mock_config = MagicMock()
    mock_config.get.return_value = True

    mgr = notif_module.NotificationManager(mock_webview, mock_config)

    user_content = mock_webview.get_user_content_manager.return_value
    user_content.register_script_message_handler.assert_called_once_with(
        notif_module.NotificationManager.HANDLER_NAME
    )


@patch("whatsapp_desk.notifications.Notify")
@patch("whatsapp_desk.notifications.WebKit")
def test_notification_manager_injects_js(mock_webkit, mock_notify):
    """Debe inyectar el script de monitoreo en el WebView."""
    notif_module.NOTIFY_AVAILABLE = True

    mock_webview = MagicMock()
    mock_config = MagicMock()
    mock_config.get.return_value = True

    mgr = notif_module.NotificationManager(mock_webview, mock_config)

    # Verificar que se inyectó JavaScript
    mock_webview.inject_javascript.assert_called_once()


@patch("whatsapp_desk.notifications.Notify")
@patch("whatsapp_desk.notifications.WebKit")
def test_no_notification_when_disabled(mock_webkit, mock_notify):
    """No debe mostrar notificaciones si están desactivadas en la config."""
    notif_module.NOTIFY_AVAILABLE = True

    mock_webview = MagicMock()
    mock_config = MagicMock()

    # Configurar para que notifications_enabled sea False
    def config_get(key, default=None):
        if key == "notifications_enabled":
            return False
        return default

    mock_config.get.side_effect = config_get

    mgr = notif_module.NotificationManager(mock_webview, mock_config)

    # Simular recepción de mensaje
    mock_js_result = MagicMock()
    mock_js_value = MagicMock()
    mock_js_value.to_string.return_value = '{"count": 1}'
    mock_js_result.get_js_value.return_value = mock_js_value

    mgr._on_message_received(None, mock_js_result)

    # No debe intentar mostrar notificación
    mock_notify.Notification.new.assert_not_called()


@patch("whatsapp_desk.notifications.time")
@patch("whatsapp_desk.notifications.Notify")
@patch("whatsapp_desk.notifications.WebKit")
def test_debounce_rapid_messages(mock_webkit, mock_notify, mock_time):
    """Debe evitar notificaciones duplicadas en rápida sucesión."""
    notif_module.NOTIFY_AVAILABLE = True

    mock_webview = MagicMock()
    mock_config = MagicMock()
    mock_config.get.return_value = True

    # Simular que el tiempo avanza
    mock_time.time.side_effect = [100.0, 100.5]  # Segunda llamada solo 0.5s después

    mgr = notif_module.NotificationManager(mock_webview, mock_config)

    mock_js_result = MagicMock()
    mock_js_value = MagicMock()
    mock_js_value.to_string.return_value = '{"count": 1}'
    mock_js_result.get_js_value.return_value = mock_js_value

    # Primera notificación — debe mostrarse
    mgr._on_message_received(None, mock_js_result)
    assert mock_notify.Notification.new.call_count == 1

    # Segunda notificación — demasiado pronto, no debe mostrarse
    mgr._on_message_received(None, mock_js_result)
    assert mock_notify.Notification.new.call_count == 1
