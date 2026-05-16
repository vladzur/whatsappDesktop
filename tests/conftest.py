"""Fixtures compartidos para los tests de WhatsApp Desk."""

import os
import json
import tempfile
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def temp_config_dir(monkeypatch):
    """Proporciona un directorio temporal para archivos de configuración."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = os.path.join(tmpdir, "config")
        data_dir = os.path.join(tmpdir, "data")
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        # Sobrescribir constantes de directorio
        import whatsapp_desk.constants as const
        monkeypatch.setattr(const, "CONFIG_HOME", config_dir)
        monkeypatch.setattr(const, "DATA_HOME", data_dir)

        yield {"config": config_dir, "data": data_dir}


@pytest.fixture
def config_manager(temp_config_dir):
    """Proporciona un ConfigManager con directorio temporal."""
    from whatsapp_desk.config import ConfigManager
    return ConfigManager()


@pytest.fixture
def mock_webkit():
    """Mock para los módulos WebKit."""
    with patch("gi.repository.WebKit") as mock:
        # Configurar propiedades comunes
        mock_settings = MagicMock()
        mock.WebView.return_value.get_settings.return_value = mock_settings
        mock.WebView.return_value.get_zoom_level.return_value = 1.0
        mock.WebView.return_value.get_user_content_manager.return_value = MagicMock()
        mock.WebView.return_value.get_title.return_value = None
        mock.WebView.return_value.get_uri.return_value = None

        mock.LoadEvent.STARTED = "WEBKIT_LOAD_STARTED"
        mock.LoadEvent.FINISHED = "WEBKIT_LOAD_FINISHED"
        mock.WebProcessTerminationReason.CRASHED = "WEBKIT_WEB_PROCESS_CRASHED"
        mock.PolicyDecisionType.NAVIGATION_ACTION = "NAVIGATION_ACTION"

        yield mock


@pytest.fixture
def mock_gtk():
    """Mock para los módulos GTK."""
    with patch("gi.repository.Gtk") as mock:
        yield mock


@pytest.fixture
def mock_gio():
    """Mock para los módulos Gio."""
    with patch("gi.repository.Gio") as mock:
        yield mock
