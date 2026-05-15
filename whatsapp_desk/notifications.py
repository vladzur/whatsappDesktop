"""Notificaciones de escritorio para nuevos mensajes de WhatsApp.

Usa un puente JavaScript → Python mediante
UserContentManager.register_script_message_handler() para detectar
nuevos mensajes en el DOM de WhatsApp Web y emitir notificaciones.
"""

import time
import gi

gi.require_version("WebKit", "6.0")
from gi.repository import WebKit  # noqa: E402

NOTIFY_AVAILABLE = False

try:
    gi.require_version("Notify", "0.7")
    from gi.repository import Notify  # noqa: E402
    NOTIFY_AVAILABLE = True
except (ValueError, ImportError):
    pass

# Tiempo mínimo entre notificaciones (segundos) para evitar spam
DEBOUNCE_SECONDS = 3


class NotificationManager:
    """Administra las notificaciones de escritorio para WhatsApp Web.

    Inyecta JavaScript en el WebView que monitorea el DOM en busca
    de nuevos mensajes entrantes. Cuando detecta uno, lo comunica
    a Python mediante el puente de mensajes de WebKit.
    """

    # Nombre del handler registrado en WebKit
    HANDLER_NAME = "whatsappNotifier"

    def __init__(self, webview: WebKit.WebView, config):
        self._webview = webview
        self._config = config
        self._last_notification_time = 0

        if NOTIFY_AVAILABLE:
            Notify.init("WhatsApp Desk")
            self._register_script_handler()
            self._inject_notification_script()

    def _register_script_handler(self):
        """Registra el puente JavaScript → Python en WebKit."""
        user_content = self._webview.get_user_content_manager()
        user_content.register_script_message_handler(
            self.HANDLER_NAME
        )
        user_content.connect(
            f"script-message-received::{self.HANDLER_NAME}",
            self._on_message_received,
        )

    def _inject_notification_script(self):
        """Inyecta el JavaScript que monitorea mensajes nuevos en el DOM."""
        # El script se inyecta en la inicialización.
        # El monitoreo real comienza en load-changed == FINISHED
        # porque el DOM de WhatsApp no existe antes.
        script = """
        (function() {
            const handlerName = 'whatsappNotifier';
            let lastUnreadCount = 0;

            function checkUnread() {
                try {
                    // Contar badges de mensajes no leídos en la lista de chats
                    const badges = document.querySelectorAll(
                        'span[aria-label*="unread"]'
                    );
                    const currentCount = badges.length;

                    if (currentCount > lastUnreadCount) {
                        // Nuevo mensaje detectado
                        const msg = JSON.stringify({
                            count: currentCount,
                            previous: lastUnreadCount,
                        });
                        window.webkit.messageHandlers[handlerName].postMessage(msg);
                    }
                    lastUnreadCount = currentCount;
                } catch (e) {
                    // DOM aún no está listo — reintentar en el siguiente ciclo
                }
            }

            // Monitorear cada 2 segundos
            setInterval(checkUnread, 2000);
        })();
        """
        self._webview.inject_javascript(script)

    def _on_message_received(self, user_content, js_result):
        """Callback invocado cuando el JS detecta un nuevo mensaje."""
        if not self._config.get("notifications_enabled", True):
            return

        now = time.time()
        if now - self._last_notification_time < DEBOUNCE_SECONDS:
            return
        self._last_notification_time = now

        try:
            # Extraer el conteo del mensaje JSON del JS
            import json
            data = json.loads(
                js_result.get_js_value().to_string()
            )
            count = data.get("count", 1)
        except Exception:
            count = 1

        if count == 1:
            body = "Tienes un nuevo mensaje de WhatsApp"
        else:
            body = f"Tienes {count} nuevos mensajes de WhatsApp"

        self._show_notification("WhatsApp Desk", body)

    def _show_notification(self, title: str, body: str):
        """Muestra una notificación de escritorio."""
        if not NOTIFY_AVAILABLE:
            return

        try:
            notification = Notify.Notification.new(
                title, body, "whatsapp-desk-symbolic"
            )
            notification.set_timeout(5000)  # 5 segundos
            notification.show()
        except Exception:
            pass  # Fallar silenciosamente
