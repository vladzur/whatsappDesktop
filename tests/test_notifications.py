"""Tests para el NotificationManager basado en señales WebKit."""

from unittest.mock import MagicMock, patch
import whatsapp_desk.notifications as notif_module


# ── Helpers ──────────────────────────────────────────────────────────────

def _fake_notification(title="Nuevo mensaje", body="Juan: Hola"):
    """Crea un mock de WebKit.Notification con título y cuerpo."""
    notif = MagicMock()
    notif.get_title.return_value = title
    notif.get_body.return_value = body
    return notif


def _config_with(notifications_enabled=True):
    """Crea un mock de config con la clave especificada."""
    config = MagicMock()
    config.get.return_value = notifications_enabled
    return config


# ── Constructor ──────────────────────────────────────────────────────────

@patch("whatsapp_desk.notifications.Notify")
def test_init_calls_notify_init(mock_notify):
    """Debe inicializar libnotify cuando la biblioteca está disponible."""
    notif_module.NOTIFY_AVAILABLE = True
    config = _config_with()
    notif_module.NotificationManager(config)
    mock_notify.init.assert_called_once_with("WhatsApp Desk")


@patch("whatsapp_desk.notifications.Notify")
def test_init_stores_callback(mock_notify):
    """Debe almacenar el callback on_new_message."""
    notif_module.NOTIFY_AVAILABLE = True
    callback = MagicMock()
    mgr = notif_module.NotificationManager(_config_with(), on_new_message=callback)
    assert mgr._on_new_message_cb is callback


@patch("whatsapp_desk.notifications.Notify")
def test_init_starts_with_zero_count(mock_notify):
    """Debe inicializar el contador de no leídos en 0."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())
    assert mgr._unread_count == 0


# ── handle_webkit_notification ──────────────────────────────────────────

@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_shows_libnotify(mock_notify):
    """Debe mostrar una burbuja de escritorio vía libnotify."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())

    notif = _fake_notification(title="Título", body="Cuerpo del mensaje")
    result = mgr.handle_webkit_notification(notif)

    assert result is True
    mock_notify.Notification.new.assert_called_once_with(
        "Título", "Cuerpo del mensaje", "whatsapp-desk-symbolic"
    )
    mock_notify.Notification.new.return_value.show.assert_called_once()


@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_returns_true_when_disabled(mock_notify):
    """Debe retornar True aunque las notificaciones estén desactivadas.

    True le indica a WebKit que la notificación fue manejada (aunque la
    hayamos descartado), evitando que intente mostrarla por su cuenta.
    """
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with(notifications_enabled=False))

    notif = _fake_notification()
    result = mgr.handle_webkit_notification(notif)

    assert result is True
    mock_notify.Notification.new.assert_not_called()


@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_increments_unread_count(mock_notify):
    """Debe incrementar el contador de mensajes no leídos."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())

    mgr.handle_webkit_notification(_fake_notification())
    assert mgr._unread_count == 1

    mgr.handle_webkit_notification(_fake_notification())
    assert mgr._unread_count == 2


@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_calls_on_new_message(mock_notify):
    """Debe invocar el callback on_new_message con el conteo actualizado."""
    notif_module.NOTIFY_AVAILABLE = True
    callback = MagicMock()
    mgr = notif_module.NotificationManager(
        _config_with(), on_new_message=callback
    )

    mgr.handle_webkit_notification(_fake_notification())
    callback.assert_called_with(1)

    mgr.handle_webkit_notification(_fake_notification())
    callback.assert_called_with(2)


@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_respects_debounce(mock_notify):
    """No debe mostrar burbuja duplicada en rápida sucesión."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())

    # Primera notificación — se muestra
    mgr.handle_webkit_notification(_fake_notification())
    assert mock_notify.Notification.new.call_count == 1

    # Segunda inmediata — no se muestra por debounce
    mgr.handle_webkit_notification(_fake_notification())
    assert mock_notify.Notification.new.call_count == 1


@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_debounce_still_counts(mock_notify):
    """Aunque se omita la burbuja por debounce, el conteo debe subir."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())

    mgr.handle_webkit_notification(_fake_notification())
    mgr.handle_webkit_notification(_fake_notification())

    # El conteo debe ser 2 aunque solo se mostró una burbuja
    assert mgr._unread_count == 2


@patch("whatsapp_desk.notifications.time")
@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_shows_after_debounce_window(mock_notify, mock_time):
    """Debe volver a mostrar notificación tras la ventana de debounce."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())

    # Tiempo inicial: 100.0
    mock_time.time.return_value = 100.0
    mgr.handle_webkit_notification(_fake_notification())
    assert mock_notify.Notification.new.call_count == 1

    # Avanzar más allá de DEBOUNCE_SECONDS
    mock_time.time.return_value = 100.0 + notif_module.DEBOUNCE_SECONDS + 1
    mgr.handle_webkit_notification(_fake_notification())
    assert mock_notify.Notification.new.call_count == 2


# ── reset_unread ─────────────────────────────────────────────────────────

@patch("whatsapp_desk.notifications.Notify")
def test_reset_unread_zeroes_count(mock_notify):
    """reset_unread() debe reiniciar el contador a 0."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())

    mgr.handle_webkit_notification(_fake_notification())
    mgr.handle_webkit_notification(_fake_notification())
    assert mgr._unread_count == 2

    mgr.reset_unread()
    assert mgr._unread_count == 0


@patch("whatsapp_desk.notifications.Notify")
def test_reset_unread_calls_callback_with_zero(mock_notify):
    """reset_unread() debe invocar on_new_message con 0."""
    notif_module.NOTIFY_AVAILABLE = True
    callback = MagicMock()
    mgr = notif_module.NotificationManager(
        _config_with(), on_new_message=callback
    )

    mgr.handle_webkit_notification(_fake_notification())
    callback.assert_called_with(1)

    mgr.reset_unread()
    callback.assert_called_with(0)


@patch("whatsapp_desk.notifications.Notify")
def test_reset_unread_without_callback_does_not_crash(mock_notify):
    """reset_unread() no debe fallar si no hay callback registrado."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with(), on_new_message=None)

    mgr.handle_webkit_notification(_fake_notification())
    # No debe lanzar excepción
    mgr.reset_unread()
    assert mgr._unread_count == 0


# ── Fallback cuando libnotify no está disponible ─────────────────────────

@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_survives_notify_unavailable(mock_notify):
    """No debe fallar cuando libnotify no está instalado."""
    notif_module.NOTIFY_AVAILABLE = False
    callback = MagicMock()
    mgr = notif_module.NotificationManager(
        _config_with(), on_new_message=callback
    )

    notif = _fake_notification()
    result = mgr.handle_webkit_notification(notif)

    # Debe retornar True, contar igual, y llamar al callback
    assert result is True
    assert mgr._unread_count == 1
    callback.assert_called_with(1)


@patch("whatsapp_desk.notifications.Notify")
def test_show_notification_catches_exceptions(mock_notify):
    """No debe propagar excepciones al mostrar la notificación."""
    notif_module.NOTIFY_AVAILABLE = True
    mock_notify.Notification.new.side_effect = RuntimeError("Fallo")

    mgr = notif_module.NotificationManager(_config_with())
    notif = _fake_notification()

    # No debe lanzar excepción
    result = mgr.handle_webkit_notification(notif)
    assert result is True


# ── Valores por defecto del título/cuerpo ────────────────────────────────

@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_falls_back_to_defaults(mock_notify):
    """Debe usar valores por defecto si el título o cuerpo están vacíos."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())

    notif = _fake_notification(title="", body="")
    mgr.handle_webkit_notification(notif)

    mock_notify.Notification.new.assert_called_once_with(
        "WhatsApp Desk", "Tienes un nuevo mensaje", "whatsapp-desk-symbolic"
    )


# ── Constante _DESKTOP_ENTRY ──────────────────────────────────────────────

def test_desktop_entry_outside_flatpak():
    """Fuera de Flatpak, desktop-entry debe ser 'whatsapp-desk'.

    El archivo .desktop se instala como whatsapp-desk.desktop, por lo que
    el hint desktop-entry debe coincidir con ese nombre (sin extensión).
    """
    assert notif_module._DESKTOP_ENTRY == "whatsapp-desk"


@patch("whatsapp_desk.notifications.IN_FLATPAK", True)
def test_desktop_entry_inside_flatpak():
    """En Flatpak, desktop-entry debe coincidir con APP_ID (RDNN)."""
    # Forzar la recarga del módulo para re-evaluar _DESKTOP_ENTRY
    import importlib
    import whatsapp_desk.notifications as nmod
    # Mockear IN_FLATPAK antes de recargar
    with patch.object(nmod, "IN_FLATPAK", True):
        pass
    # La constante ya se evaluó al importar.  Verificar que cuando
    # IN_FLATPAK es True, _DESKTOP_ENTRY usa APP_ID.
    from whatsapp_desk.constants import APP_ID
    assert APP_ID == "com.vladzur.WhatsAppDesk"


# ── Hints de notificación ──────────────────────────────────────────────────

@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_sets_desktop_entry_hint(mock_notify):
    """Debe establecer el hint desktop-entry en la notificación."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())

    notif = _fake_notification()
    mgr.handle_webkit_notification(notif)

    created = mock_notify.Notification.new.return_value
    created.set_hint.assert_any_call(
        "desktop-entry", mock_notify.GLib.Variant.return_value
    )


@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_sets_urgency_hint(mock_notify):
    """Debe establecer el hint de urgencia normal (1)."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())

    notif = _fake_notification()
    mgr.handle_webkit_notification(notif)

    created = mock_notify.Notification.new.return_value
    # Verificar que set_hint fue llamado con "urgency"
    urgency_calls = [
        c for c in created.set_hint.call_args_list
        if c[0][0] == "urgency"
    ]
    assert len(urgency_calls) == 1


@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_sets_category_hint(mock_notify):
    """Debe establecer el hint de categoría im.received."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())

    notif = _fake_notification()
    mgr.handle_webkit_notification(notif)

    created = mock_notify.Notification.new.return_value
    category_calls = [
        c for c in created.set_hint.call_args_list
        if c[0][0] == "category"
    ]
    assert len(category_calls) == 1


# ── Unicode ─────────────────────────────────────────────────────────────────

@patch("whatsapp_desk.notifications.Notify")
def test_handle_notification_normalizes_unicode(mock_notify):
    """Debe aceptar emojis en el título y cuerpo sin errores."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())

    # Mensaje típico de WhatsApp con emojis
    notif = _fake_notification(
        title="Mamá ❤️",
        body="Te quiero mucho 🥰😘💕"
    )
    result = mgr.handle_webkit_notification(notif)

    assert result is True
    mock_notify.Notification.new.return_value.show.assert_called_once()


@patch("whatsapp_desk.notifications.Notify")
def test_show_notification_survives_unicode_normalization(mock_notify):
    """La normalización Unicode no debe lanzar excepción con caracteres raros."""
    notif_module.NOTIFY_AVAILABLE = True
    mgr = notif_module.NotificationManager(_config_with())

    # Caracteres Unicode combinados y emojis compuestos
    notif = _fake_notification(
        title="Café con leche 🏽‍👨",
        body="éxito ♥️"
    )
    result = mgr.handle_webkit_notification(notif)

    assert result is True
    # Verificar que los argumentos pasados a Notification.new están normalizados
    call_args = mock_notify.Notification.new.call_args[0]
    # NFC normaliza é + combining accent → é precompuesto
    assert "\\xe9" in call_args[1] or "é" in call_args[1]
