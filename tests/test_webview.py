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
