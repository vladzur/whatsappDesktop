"""Tests para el UrlHandler."""

from unittest.mock import MagicMock, patch
from whatsapp_desk.url_handler import UrlHandler, WHATSAPP_DOMAINS


@patch("whatsapp_desk.url_handler.Gio")
def test_whatsapp_url_allowed(mock_gio):
    """URLs de WhatsApp deben permitirse en el WebView."""
    mock_webview = MagicMock()
    handler = UrlHandler(mock_webview)

    # Verificar dominios de WhatsApp
    assert handler._is_whatsapp_url("https://web.whatsapp.com/")
    assert handler._is_whatsapp_url("https://whatsapp.com/")
    assert handler._is_whatsapp_url("https://faq.whatsapp.com/help")

    # Conectar decide-policy debe haberse llamado
    mock_webview.connect.assert_called_once_with(
        "decide-policy", handler._on_decide_policy
    )


@patch("whatsapp_desk.url_handler.Gio")
def test_external_url_blocked(mock_gio):
    """URLs externas deben bloquearse en el WebView y abrirse en navegador."""
    mock_webview = MagicMock()
    handler = UrlHandler(mock_webview)

    assert not handler._is_whatsapp_url("https://google.com")
    assert not handler._is_whatsapp_url("https://github.com")
    assert not handler._is_whatsapp_url("https://evil-whatsapp.com")


@patch("whatsapp_desk.url_handler.Gio")
def test_open_external_launches_browser(mock_gio):
    """_open_external() debe usar Gio.AppInfo para abrir el navegador."""
    mock_webview = MagicMock()
    handler = UrlHandler(mock_webview)

    handler._open_external("https://example.com")
    mock_gio.AppInfo.launch_default_for_uri.assert_called_once_with(
        "https://example.com"
    )


@patch("whatsapp_desk.url_handler.Gio")
def test_decide_policy_allows_whatsapp_navigation(mock_gio):
    """La señal decide-policy debe permitir navegación en WhatsApp."""
    mock_webview = MagicMock()
    handler = UrlHandler(mock_webview)

    mock_decision = MagicMock()
    mock_nav_action = MagicMock()
    mock_request = MagicMock()
    mock_request.get_uri.return_value = "https://web.whatsapp.com/"
    mock_nav_action.get_request.return_value = mock_request
    mock_decision.get_navigation_action.return_value = mock_nav_action

    from gi.repository import WebKit as WebKitMock

    # Usar el enum real para NAVIGATION_ACTION
    result = handler._on_decide_policy(
        mock_webview,
        mock_decision,
        "NAVIGATION_ACTION",
    )

    assert result is False  # False = permitir
