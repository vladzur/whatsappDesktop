"""Tests para el WhatsAppWebView."""

from unittest.mock import MagicMock, patch, call
from whatsapp_desk.webview import WhatsAppWebView
from whatsapp_desk.resources.ua_chrome import CHROME_USER_AGENT


@patch("whatsapp_desk.webview.WebKit")
def test_user_agent_set_to_chrome(mock_webkit):
    """El User-Agent debe configurarse como Chrome para evadir bloqueo."""
    mock_settings = MagicMock()
    mock_webkit.WebView.__init__.return_value = None
    mock_webkit.WebView.get_settings.return_value = mock_settings

    wv = WhatsAppWebView()
    wv.get_settings = MagicMock(return_value=mock_settings)

    # Reconstruir: el __init__ real llama a _setup_settings
    wv._setup_settings()

    mock_settings.set_property.assert_any_call("user-agent", CHROME_USER_AGENT)


@patch("whatsapp_desk.webview.WebKit")
def test_javascript_enabled(mock_webkit):
    """JavaScript debe estar habilitado."""
    mock_settings = MagicMock()
    mock_webkit.WebView.__init__.return_value = None
    mock_webkit.WebView.get_settings.return_value = mock_settings

    wv = WhatsAppWebView()
    wv.get_settings = MagicMock(return_value=mock_settings)
    wv._setup_settings()

    mock_settings.set_property.assert_any_call("enable-javascript", True)


@patch("whatsapp_desk.webview.WebKit")
def test_local_storage_enabled(mock_webkit):
    """localStorage debe estar habilitado para persistencia de sesión."""
    mock_settings = MagicMock()
    mock_webkit.WebView.__init__.return_value = None
    mock_webkit.WebView.get_settings.return_value = mock_settings

    wv = WhatsAppWebView()
    wv.get_settings = MagicMock(return_value=mock_settings)
    wv._setup_settings()

    mock_settings.set_property.assert_any_call("enable-html5-local-storage", True)


@patch("whatsapp_desk.webview.WebKit")
def test_clipboard_access_enabled(mock_webkit):
    """Debe permitir acceso al portapapeles desde JavaScript."""
    mock_settings = MagicMock()
    mock_webkit.WebView.__init__.return_value = None
    mock_webkit.WebView.get_settings.return_value = mock_settings

    wv = WhatsAppWebView()
    wv.get_settings = MagicMock(return_value=mock_settings)
    wv._setup_settings()

    mock_settings.set_property.assert_any_call("javascript-can-access-clipboard", True)


@patch("whatsapp_desk.webview.WebKit")
def test_webgl_enabled(mock_webkit):
    """WebGL debe estar habilitado para rendimiento gráfico."""
    mock_settings = MagicMock()
    mock_webkit.WebView.__init__.return_value = None
    mock_webkit.WebView.get_settings.return_value = mock_settings

    wv = WhatsAppWebView()
    wv.get_settings = MagicMock(return_value=mock_settings)
    wv._setup_settings()

    mock_settings.set_property.assert_any_call("enable-webgl", True)


@patch("whatsapp_desk.webview.WebKit")
def test_network_session_set_on_webview(mock_webkit):
    """Debe asignar la NetworkSession al WebView si se proporciona."""
    mock_webkit.WebView.__init__.return_value = None
    mock_settings = MagicMock()
    mock_webkit.WebView.get_settings.return_value = mock_settings

    mock_ns = MagicMock()
    wv = WhatsAppWebView(network_session=mock_ns)
    wv._setup_settings()

    # Usando set_property de la clase base mockeada
    # Verificar que el constructor llama a set_property
    wv.set_property.assert_called_with("network-session", mock_ns)


@patch("whatsapp_desk.webview.WebKit")
def test_load_whatsapp_loads_correct_url(mock_webkit):
    """load_whatsapp() debe cargar la URL de WhatsApp Web."""
    mock_webkit.WebView.__init__.return_value = None
    mock_settings = MagicMock()
    mock_webkit.WebView.get_settings.return_value = mock_settings

    wv = WhatsAppWebView()
    wv.load_uri = MagicMock()
    wv._setup_settings()

    wv.load_whatsapp()
    wv.load_uri.assert_called_once_with("https://web.whatsapp.com/")


# ── Inyección JS de notificaciones ────────────────────────────────────────

@patch("whatsapp_desk.webview.WebKit")
def test_spoof_script_contains_permissions_api_patch(mock_webkit):
    """El script de DOCUMENT_START debe parchear navigator.permissions.query."""
    mock_webkit.WebView.__init__.return_value = None
    mock_webkit.WebView.get_settings.return_value = MagicMock()
    mock_webkit.UserScriptInjectionTime.START = "start"
    mock_webkit.UserContentInjectedFrames.ALL_FRAMES = "all"

    wv = WhatsAppWebView.__new__(WhatsAppWebView)
    wv.get_settings = MagicMock()
    wv.set_settings = MagicMock()
    wv._setup_settings = MagicMock()
    wv.connect = MagicMock()

    user_content = MagicMock()
    wv.get_user_content_manager = MagicMock(return_value=user_content)

    # Llamar al método real de inyección
    WhatsAppWebView._inject_browser_spoof(wv)

    # Obtener el script inyectado
    assert user_content.add_script.call_count >= 1
    script_arg = user_content.add_script.call_args_list[0][0][0]
    assert "navigator.permissions" in script_arg
    assert "permissions.query" in script_arg


@patch("whatsapp_desk.webview.WebKit")
def test_spoof_script_does_not_use_patched_notification_subclass(mock_webkit):
    """El spoof NO debe usar PatchedNotification (extender la clase rompe
    la señal show-notification en WebKitGTK 6.0)."""
    mock_webkit.WebView.__init__.return_value = None
    mock_webkit.WebView.get_settings.return_value = MagicMock()
    mock_webkit.UserScriptInjectionTime.START = "start"
    mock_webkit.UserContentInjectedFrames.ALL_FRAMES = "all"

    wv = WhatsAppWebView.__new__(WhatsAppWebView)
    wv.get_settings = MagicMock()
    wv.set_settings = MagicMock()
    wv._setup_settings = MagicMock()
    wv.connect = MagicMock()

    user_content = MagicMock()
    wv.get_user_content_manager = MagicMock(return_value=user_content)

    WhatsAppWebView._inject_browser_spoof(wv)

    # El script no debe contener PatchedNotification
    script_arg = user_content.add_script.call_args_list[0][0][0]
    assert "PatchedNotification" not in script_arg
    # Debe parchear directamente la propiedad permission
    assert "Object.defineProperty(Notification, 'permission'" in script_arg or \
        "Object.defineProperty(window, 'Notification'" in script_arg


@patch("whatsapp_desk.webview.WebKit")
def test_notification_fallback_injects_at_document_end(mock_webkit):
    """El fallback de notificación debe inyectarse en DOCUMENT_END."""
    mock_webkit.WebView.__init__.return_value = None
    mock_webkit.WebView.get_settings.return_value = MagicMock()
    mock_webkit.UserScriptInjectionTime.START = "start"
    mock_webkit.UserScriptInjectionTime.END = "end"
    mock_webkit.UserContentInjectedFrames.ALL_FRAMES = "all"

    wv = WhatsAppWebView.__new__(WhatsAppWebView)
    wv.get_settings = MagicMock()
    wv.set_settings = MagicMock()
    wv._setup_settings = MagicMock()
    wv.connect = MagicMock()

    user_content = MagicMock()
    wv.get_user_content_manager = MagicMock(return_value=user_content)

    WhatsAppWebView._inject_notification_fallback(wv)

    assert user_content.add_script.call_count == 1
    call_args = user_content.add_script.call_args
    script = call_args[0][0]
    injection_time = call_args[0][2]
    assert injection_time == "end"
    assert "Notification.permission !== 'granted'" in script
    assert "permissions.query" in script


@patch("whatsapp_desk.webview.WebKit")
def test_audio_mute_injects_html_audio_element_patch(mock_webkit):
    """La inyección de muteo debe interceptar HTMLAudioElement.play()."""
    mock_webkit.WebView.__init__.return_value = None
    mock_webkit.WebView.get_settings.return_value = MagicMock()
    mock_webkit.UserScriptInjectionTime.START = "start"
    mock_webkit.UserContentInjectedFrames.ALL_FRAMES = "all"

    wv = WhatsAppWebView.__new__(WhatsAppWebView)
    wv.get_settings = MagicMock()
    wv.set_settings = MagicMock()
    wv._setup_settings = MagicMock()
    wv.connect = MagicMock()

    user_content = MagicMock()
    wv.get_user_content_manager = MagicMock(return_value=user_content)

    WhatsAppWebView._inject_audio_mute(wv)

    assert user_content.add_script.call_count == 1
    script_arg = user_content.add_script.call_args_list[0][0][0]
    assert "HTMLAudioElement.prototype.play" in script_arg
    assert "notification" in script_arg.lower()
