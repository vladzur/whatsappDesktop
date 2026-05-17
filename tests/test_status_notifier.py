"""Tests para el StatusNotifierItem con D-Bus y badge de mensajes no leídos."""

from unittest.mock import MagicMock, patch, call
import whatsapp_desk.status_notifier as sni_module


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_sni(mock_init_dbus=True):
    """Crea un StatusNotifierItem con D-Bus mockeado.

    Si ``mock_init_dbus`` es True, ``_init_dbus()`` es un no-op para
    evitar conexiones reales al bus de sesión. Los iconos en disco
    también se mockean.
    """
    with patch.object(sni_module.StatusNotifierItem, "_init_dbus"):
        with patch("whatsapp_desk.status_notifier._ensure_unread_icon_installed"):
            with patch("whatsapp_desk.status_notifier._ensure_symbolic_icon_installed"):
                mock_app = MagicMock()
                mock_window = MagicMock()
                return sni_module.StatusNotifierItem(mock_app, mock_window)


# ── set_unread ───────────────────────────────────────────────────────────

def test_set_unread_changes_icon_to_unread():
    """set_unread con count > 0 debe cambiar al icono de badge."""
    sni = _make_sni()
    sni._current_icon = sni_module._ICON_NORMAL  # asegurar estado inicial
    sni._emit_new_icon = MagicMock()

    sni.set_unread(3)

    assert sni._current_icon == sni_module._ICON_UNREAD


def test_set_unread_emits_new_icon():
    """Al cambiar a estado unread debe emitir la señal NewIcon."""
    sni = _make_sni()
    sni._current_icon = sni_module._ICON_NORMAL
    sni._registered = True  # debe estar registrado para emitir
    sni._connection = MagicMock()
    sni._emit_new_icon = MagicMock()

    sni.set_unread(1)
    sni._emit_new_icon.assert_called_once()


def test_set_unread_with_zero_delegates_to_clear():
    """set_unread(0) debe delegar en clear_unread()."""
    sni = _make_sni()
    sni._current_icon = sni_module._ICON_UNREAD
    sni.clear_unread = MagicMock()

    sni.set_unread(0)
    sni.clear_unread.assert_called_once()


def test_set_unread_when_already_unread_is_noop():
    """No debe emitir señal redundante si ya está en estado unread."""
    sni = _make_sni()
    sni._current_icon = sni_module._ICON_UNREAD
    sni._emit_new_icon = MagicMock()

    sni.set_unread(5)
    sni._emit_new_icon.assert_not_called()


def test_set_unread_negative_delegates_to_clear():
    """set_unread con count negativo debe limpiar el badge."""
    sni = _make_sni()
    sni.clear_unread = MagicMock()

    sni.set_unread(-1)
    sni.clear_unread.assert_called_once()


# ── clear_unread ─────────────────────────────────────────────────────────

def test_clear_unread_restores_icon():
    """clear_unread debe volver al icono normal."""
    sni = _make_sni()
    sni._current_icon = sni_module._ICON_UNREAD
    sni._emit_new_icon = MagicMock()

    sni.clear_unread()

    assert sni._current_icon == sni_module._ICON_NORMAL


def test_clear_unread_emits_new_icon():
    """Al limpiar el badge debe emitir la señal NewIcon."""
    sni = _make_sni()
    sni._current_icon = sni_module._ICON_UNREAD
    sni._registered = True
    sni._connection = MagicMock()
    sni._emit_new_icon = MagicMock()

    sni.clear_unread()
    sni._emit_new_icon.assert_called_once()


def test_clear_unread_when_already_clean_is_noop():
    """No debe emitir señal redundante si ya está en estado normal."""
    sni = _make_sni()
    sni._current_icon = sni_module._ICON_NORMAL
    sni._emit_new_icon = MagicMock()

    sni.clear_unread()
    sni._emit_new_icon.assert_not_called()


# ── Ciclo completo set → clear ───────────────────────────────────────────

def test_set_unread_then_clear_returns_to_normal():
    """Un ciclo set_unread + clear_unread debe volver al icono normal."""
    sni = _make_sni()
    sni._emit_new_icon = MagicMock()

    sni.set_unread(2)
    assert sni._current_icon == sni_module._ICON_UNREAD

    sni.clear_unread()
    assert sni._current_icon == sni_module._ICON_NORMAL


def test_multiple_set_unread_keeps_badge():
    """Múltiples llamadas a set_unread deben mantener el icono de badge."""
    sni = _make_sni()
    sni._emit_new_icon = MagicMock()

    sni.set_unread(1)
    sni.set_unread(2)
    sni.set_unread(5)

    # El icono sigue en estado unread
    assert sni._current_icon == sni_module._ICON_UNREAD


# ── _emit_new_icon ──────────────────────────────────────────────────────

def test_emit_new_icon_sends_dbus_signal():
    """Debe emitir la señal NewIcon del protocolo SNI por D-Bus."""
    sni = _make_sni()
    sni._registered = True
    sni._connection = MagicMock()

    sni._emit_new_icon()

    sni._connection.emit_signal.assert_called_once_with(
        None,
        sni_module.SNI_PATH,
        "org.kde.StatusNotifierItem",
        "NewIcon",
        None,
    )


def test_emit_new_icon_skips_when_not_registered():
    """No debe intentar emitir D-Bus si no está registrado en el Watcher."""
    sni = _make_sni()
    sni._registered = False
    sni._connection = MagicMock()

    sni._emit_new_icon()

    sni._connection.emit_signal.assert_not_called()


def test_emit_new_icon_skips_when_no_connection():
    """No debe fallar si no hay conexión D-Bus (_connection es None)."""
    sni = _make_sni()
    sni._registered = True
    sni._connection = None

    # No debe lanzar excepción
    sni._emit_new_icon()


def test_emit_new_icon_catches_dbus_exceptions():
    """No debe propagar excepciones del bus D-Bus."""
    sni = _make_sni()
    sni._registered = True
    sni._connection = MagicMock()
    sni._connection.emit_signal.side_effect = RuntimeError("D-Bus caído")

    # No debe lanzar excepción
    sni._emit_new_icon()


# ── is_available ─────────────────────────────────────────────────────────

def test_is_available_when_registered():
    """is_available debe retornar True cuando está registrado en el Watcher."""
    sni = _make_sni()
    sni._registered = True
    assert sni.is_available() is True


def test_is_available_when_not_registered():
    """is_available debe retornar False cuando no se registró en el Watcher."""
    sni = _make_sni()
    sni._registered = False
    assert sni.is_available() is False


# ── Instalación de iconos en runtime ────────────────────────────────────

def test_ensure_unread_icon_creates_file(tmp_path):
    """_ensure_unread_icon_installed debe crear el SVG con badge si no existe."""
    unread_path = tmp_path / "whatsapp-desk-unread-symbolic.svg"
    with patch("whatsapp_desk.status_notifier._ICON_UNREAD_PATH", str(unread_path)):
        with patch("whatsapp_desk.status_notifier._ICON_INSTALL_DIR", str(tmp_path)):
            sni_module._ensure_unread_icon_installed()
    assert unread_path.is_file()
    content = unread_path.read_text()
    assert "<svg" in content
    assert "whatsapp-desk-unread" not in content  # nombre de archivo, no en contenido
    assert "#e74c3c" in content  # color del badge


def test_ensure_unread_icon_skips_if_exists(tmp_path):
    """_ensure_unread_icon_installed no debe sobrescribir el archivo si ya existe."""
    unread_path = tmp_path / "whatsapp-desk-unread-symbolic.svg"
    unread_path.write_text("contenido-existente")

    with patch("whatsapp_desk.status_notifier._ICON_UNREAD_PATH", str(unread_path)):
        with patch("whatsapp_desk.status_notifier._ICON_INSTALL_DIR", str(tmp_path)):
            sni_module._ensure_unread_icon_installed()

    assert unread_path.read_text() == "contenido-existente"


def test_ensure_unread_icon_os_error_is_silent():
    """_ensure_unread_icon_installed no debe lanzar excepción si falla el FS."""
    with patch("builtins.open", side_effect=OSError("Permiso denegado")):
        # No debe lanzar excepción
        sni_module._ensure_unread_icon_installed()


# ── SVG inline del badge ────────────────────────────────────────────────

def test_unread_svg_contains_badge_circle():
    """El SVG inline debe incluir el círculo de notificación."""
    assert '<circle cx="13" cy="3" r="3"' in sni_module._ICON_UNREAD_SVG
    assert 'fill="#e74c3c"' in sni_module._ICON_UNREAD_SVG


def test_unread_svg_is_valid_xml():
    """El SVG inline debe ser XML bien formado."""
    import xml.etree.ElementTree as ET
    ET.fromstring(sni_module._ICON_UNREAD_SVG)  # no lanza excepción


# ── Constantes ───────────────────────────────────────────────────────────

def test_icon_names_are_different():
    """Los nombres de icono normal y unread deben ser distintos."""
    assert sni_module._ICON_NORMAL != sni_module._ICON_UNREAD


def test_icon_theme_dir_uses_xdg_data_home():
    """_ICON_THEME_DIR debe estar dentro de XDG_DATA_HOME."""
    assert "/.local/share/icons" in sni_module._ICON_THEME_DIR or \
        "share/icons" in sni_module._ICON_THEME_DIR
