"""Tests para el TrayIcon."""

from unittest.mock import MagicMock, patch
import whatsapp_desk.tray as tray_module


@patch("whatsapp_desk.tray.AppIndicator")
@patch("whatsapp_desk.tray.Gio")
def test_tray_creates_indicator_when_available(mock_gio, mock_appindicator):
    """Debe crear el AppIndicator cuando la biblioteca está disponible."""
    # Forzar TRAY_AVAILABLE a True
    tray_module.TRAY_AVAILABLE = True

    mock_app = MagicMock()
    mock_window = MagicMock()
    tray = tray_module.TrayIcon(mock_app, mock_window)

    assert tray.is_available()
    mock_appindicator.Indicator.new.assert_called_once()


@patch("whatsapp_desk.tray.AppIndicator")
@patch("whatsapp_desk.tray.Gio")
def test_tray_handles_indicator_failure_gracefully(mock_gio, mock_appindicator):
    """Debe manejar fallos al crear el indicador sin lanzar excepciones."""
    tray_module.TRAY_AVAILABLE = True
    mock_appindicator.Indicator.new.side_effect = RuntimeError("No se puede crear")

    mock_app = MagicMock()
    mock_window = MagicMock()
    tray = tray_module.TrayIcon(mock_app, mock_window)

    assert not tray.is_available()


def test_tray_not_available_when_library_missing():
    """Cuando TRAY_AVAILABLE es False, is_available() debe retornar False."""
    tray_module.TRAY_AVAILABLE = False

    mock_app = MagicMock()
    mock_window = MagicMock()
    tray = tray_module.TrayIcon(mock_app, mock_window)

    assert not tray.is_available()


@patch("whatsapp_desk.tray.AppIndicator")
@patch("whatsapp_desk.tray.Gio")
def test_show_window_presents_window(mock_gio, mock_appindicator):
    """show_window() debe llamar a window.present()."""
    tray_module.TRAY_AVAILABLE = True

    mock_app = MagicMock()
    mock_window = MagicMock()
    tray = tray_module.TrayIcon(mock_app, mock_window)

    tray.show_window()
    mock_window.present.assert_called_once()
