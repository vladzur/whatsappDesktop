"""Tests para el WebViewManager."""

import os
from unittest.mock import patch, MagicMock
from whatsapp_desk.webview_manager import WebViewManager


@patch("whatsapp_desk.webview_manager.GObject")
@patch("whatsapp_desk.webview_manager.WebKit")
def test_creates_data_directory(mock_webkit, mock_gobject, temp_config_dir):
    """Debe crear el directorio de datos al inicializar."""
    mgr = WebViewManager()
    assert os.path.isdir(os.path.join(temp_config_dir["data"], "webkit-data"))
    assert os.path.isdir(os.path.join(temp_config_dir["data"], "webkit-cache"))


@patch("whatsapp_desk.webview_manager.GObject")
@patch("whatsapp_desk.webview_manager.WebKit")
def test_get_network_session_creates_session(mock_webkit, mock_gobject, temp_config_dir):
    """get_network_session() debe crear una NetworkSession con los paths correctos."""
    mgr = WebViewManager()
    session = mgr.get_network_session()

    mock_gobject.new.assert_called_once()
    call_args = mock_gobject.new.call_args
    # Verificar que se pasaron los argumentos correctos
    assert call_args[0][0] == mock_webkit.NetworkSession
    assert "data_directory" in call_args[1]
    assert "cache_directory" in call_args[1]
    assert call_args[1]["is_ephemeral"] is False


@patch("whatsapp_desk.webview_manager.GObject")
@patch("whatsapp_desk.webview_manager.WebKit")
def test_get_network_session_reuses_session(mock_webkit, mock_gobject, temp_config_dir):
    """get_network_session() debe reutilizar la sesión en llamadas sucesivas."""
    mgr = WebViewManager()
    s1 = mgr.get_network_session()
    s2 = mgr.get_network_session()
    assert s1 is s2
    # GObject.new solo debe llamarse una vez
    assert mock_gobject.new.call_count == 1


@patch("whatsapp_desk.webview_manager.GObject")
@patch("whatsapp_desk.webview_manager.WebKit")
def test_clear_session_resets_state(mock_webkit, mock_gobject, temp_config_dir):
    """clear_session() debe eliminar y recrear los directorios."""
    mgr = WebViewManager()
    mgr.get_network_session()

    data_dir = os.path.join(temp_config_dir["data"], "webkit-data")
    assert os.path.isdir(data_dir)

    mgr.clear_session()
    # Después de clear, el directorio debe existir (recreado)
    assert os.path.isdir(data_dir)
    # La sesión debe ser None para forzar recreación
    assert mgr._network_session is None
