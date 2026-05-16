"""Tests para la WhatsAppDeskApplication."""

from unittest.mock import MagicMock, patch
from whatsapp_desk.application import WhatsAppDeskApplication


@patch("whatsapp_desk.application.Gtk")
@patch("whatsapp_desk.application.Gio")
@patch("whatsapp_desk.application.GLib")
@patch("whatsapp_desk.application.signal")
def test_app_id_is_set(mock_signal, mock_glib, mock_gio, mock_gtk):
    """La aplicación debe tener el APP_ID correcto registrado."""
    # Mock Application.__init__ para evitar inicialización real
    mock_gtk.Application.__init__ = MagicMock()
    app = WhatsAppDeskApplication()

    # Verificar que se llamó al constructor padre con el APP_ID
    mock_gtk.Application.__init__.assert_called_once()
    call_kwargs = mock_gtk.Application.__init__.call_args[1]
    assert "application_id" in call_kwargs


@patch("whatsapp_desk.application.Gtk")
@patch("whatsapp_desk.application.Gio")
@patch("whatsapp_desk.application.GLib")
@patch("whatsapp_desk.application.signal")
def test_config_initialized_on_startup(mock_signal, mock_glib, mock_gio, mock_gtk):
    """do_startup() debe inicializar ConfigManager."""
    mock_gtk.Application.__init__ = MagicMock()
    mock_gtk.Application.do_startup = MagicMock()

    app = WhatsAppDeskApplication()
    app._register_actions = MagicMock()  # Evitar registro de acciones
    app.do_startup()

    assert app.config is not None


@patch("whatsapp_desk.application.Gtk")
@patch("whatsapp_desk.application.Gio")
@patch("whatsapp_desk.application.GLib")
@patch("whatsapp_desk.application.signal")
def test_webview_manager_initialized_on_startup(mock_signal, mock_glib, mock_gio, mock_gtk):
    """do_startup() debe inicializar WebViewManager."""
    mock_gtk.Application.__init__ = MagicMock()
    mock_gtk.Application.do_startup = MagicMock()

    app = WhatsAppDeskApplication()
    app._register_actions = MagicMock()
    app.do_startup()

    assert app.webview_manager is not None


@patch("whatsapp_desk.application.Gtk")
@patch("whatsapp_desk.application.Gio")
@patch("whatsapp_desk.application.GLib")
@patch("whatsapp_desk.application.signal")
def test_actions_registered_on_startup(mock_signal, mock_glib, mock_gio, mock_gtk):
    """do_startup() debe registrar las GAction de la aplicación."""
    mock_gtk.Application.__init__ = MagicMock()
    mock_gtk.Application.do_startup = MagicMock()

    app = WhatsAppDeskApplication()
    app.add_action = MagicMock()
    app.do_startup()

    # Deben registrarse 3 acciones: show-window, clear-session, new-window
    assert app.add_action.call_count == 3
