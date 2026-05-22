"""Notificaciones de escritorio para nuevos mensajes de WhatsApp.

Usa la señal nativa ``show-notification`` de WebKit en lugar de polling JS.
Cuando WhatsApp Web llama a ``new Notification(...)``, WebKit emite esa señal
con un objeto ``WebKit.Notification`` que contiene el título y el cuerpo del
mensaje — exactamente los mismos que mostraría Chrome.

Flujo:
    WhatsApp Web
        → new Notification(title, {body})
        → WebKit emite show-notification(WebKit.Notification)
        → WhatsAppWebView._on_show_notification()
        → NotificationManager.handle_webkit_notification()
        → libnotify  (burbuja de escritorio)
        → on_new_message(count)  (callback al tray para actualizar el badge)
"""

import time
import gi

gi.require_version("WebKit", "6.0")

NOTIFY_AVAILABLE = False

try:
    gi.require_version("Notify", "0.7")
    from gi.repository import Notify, GLib  # noqa: E402
    NOTIFY_AVAILABLE = True
except (ValueError, ImportError):
    pass

from whatsapp_desk.constants import APP_ID, IN_FLATPAK  # noqa: E402

# Icono de la aplicación (coincide con el IconName del StatusNotifierItem)
_ICON_NORMAL = (
    "com.vladzur.WhatsAppDesk-symbolic" if IN_FLATPAK
    else "whatsapp-desk-symbolic"
)

# Tiempo mínimo entre notificaciones (segundos) para evitar spam
DEBOUNCE_SECONDS = 3


class NotificationManager:
    """Administra las notificaciones de escritorio para WhatsApp Web.

    En lugar de inyectar JavaScript de polling, escucha la señal
    ``show-notification`` de WebKit, que se dispara cuando WhatsApp Web
    invoca la Notifications API nativa del navegador.

    Parameters
    ----------
    config:
        Objeto ConfigManager con la clave ``notifications_enabled``.
    on_new_message:
        Callable opcional ``(count: int) -> None`` invocado cada vez que
        se recibe una notificación nueva. El tray lo usa para actualizar
        el badge. Si es ``None`` no se notifica al tray.
    """

    def __init__(self, config, on_new_message=None):
        self._config = config
        self._on_new_message_cb = on_new_message
        self._last_notification_time = 0
        self._unread_count = 0

        if NOTIFY_AVAILABLE:
            Notify.init(APP_ID)

    # ── API pública ───────────────────────────────────────────────────────

    def handle_webkit_notification(self, notification) -> bool:
        """Procesa una notificación nativa de WebKit.

        Parameters
        ----------
        notification:
            Objeto ``WebKit.Notification`` recibido en la señal
            ``show-notification`` del WebView.

        Returns
        -------
        bool
            ``True`` para indicarle a WebKit que la notificación fue
            manejada (evita que intente mostrarla él mismo).
        """
        if not self._config.get("notifications_enabled", True):
            return True

        now = time.time()
        if now - self._last_notification_time < DEBOUNCE_SECONDS:
            # Aunque omitimos la burbuja por debounce, el conteo sí sube
            self._unread_count += 1
            self._notify_tray()
            return True

        self._last_notification_time = now
        self._unread_count += 1

        title = notification.get_title() or "WhatsApp Desk"
        body = notification.get_body() or "Tienes un nuevo mensaje"

        self._show_notification(title, body)
        self._notify_tray()
        return True

    def reset_unread(self):
        """Reinicia el contador de mensajes no leídos (llamar al mostrar ventana)."""
        self._unread_count = 0
        if self._on_new_message_cb is not None:
            self._on_new_message_cb(0)

    # ── Internos ──────────────────────────────────────────────────────────

    def _notify_tray(self):
        """Invoca el callback del tray con el conteo actualizado."""
        if self._on_new_message_cb is not None:
            self._on_new_message_cb(self._unread_count)

    def _show_notification(self, title: str, body: str):
        """Muestra una notificación de escritorio con libnotify."""
        if not NOTIFY_AVAILABLE:
            return
        try:
            notification = Notify.Notification.new(
                title, body, _ICON_NORMAL
            )
            # El hint desktop-entry es obligatorio para que GNOME Shell
            # muestre la notificación en el feed y la asocie con la app.
            notification.set_hint("desktop-entry", GLib.Variant("s", APP_ID))
            notification.set_timeout(5000)  # 5 segundos
            notification.show()
        except Exception:
            pass  # Fallar silenciosamente
