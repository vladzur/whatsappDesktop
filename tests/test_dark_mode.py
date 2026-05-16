"""Tests para el DarkModeManager."""

from unittest.mock import MagicMock, patch
from whatsapp_desk.dark_mode import DarkModeManager


@patch("whatsapp_desk.dark_mode.Gtk")
def test_dark_mode_apply_sets_gtk_setting(mock_gtk):
    """apply() debe establecer la preferencia de tema oscuro en GTK."""
    mock_settings = MagicMock()
    mock_gtk.Settings.get_default.return_value = mock_settings

    mock_webview = MagicMock()
    mock_config = MagicMock()
    mock_config.get.return_value = True  # dark_mode activado

    manager = DarkModeManager(mock_webview, mock_config)

    mock_settings.set_property.assert_called_with(
        "gtk-application-prefer-dark-theme", True
    )


@patch("whatsapp_desk.dark_mode.Gtk")
def test_toggle_returns_new_value(mock_gtk):
    """toggle() debe retornar el nuevo valor y persistirlo."""
    mock_settings = MagicMock()
    mock_gtk.Settings.get_default.return_value = mock_settings

    mock_webview = MagicMock()
    mock_config = MagicMock()

    # Simular toggle: dark_mode pasa de False a True
    initial_values = {"dark_mode": False}

    def config_get(key, default=None):
        return initial_values.get(key, default)

    def config_toggle(key):
        initial_values[key] = not initial_values[key]
        return initial_values[key]

    mock_config.get.side_effect = config_get
    mock_config.toggle.side_effect = config_toggle

    manager = DarkModeManager(mock_webview, mock_config)
    result = manager.toggle()

    assert result is True
    mock_config.toggle.assert_called_once_with("dark_mode")


@patch("whatsapp_desk.dark_mode.Gtk")
def test_apply_reads_config(mock_gtk):
    """apply() debe leer la preferencia desde ConfigManager."""
    mock_settings = MagicMock()
    mock_gtk.Settings.get_default.return_value = mock_settings

    mock_webview = MagicMock()
    mock_config = MagicMock()
    mock_config.get.return_value = False  # dark_mode desactivado

    manager = DarkModeManager(mock_webview, mock_config)

    mock_settings.set_property.assert_called_with(
        "gtk-application-prefer-dark-theme", False
    )
