"""WebView de WhatsApp con configuración personalizada."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import GObject, Gtk, WebKit  # noqa: E402

from whatsapp_desk.constants import WHATSAPP_URL
from whatsapp_desk.resources.ua_chrome import CHROME_USER_AGENT


class WhatsAppWebView(WebKit.WebView):
    """WebView configurado específicamente para WhatsApp Web.

    Aplica un User-Agent de Chrome para evadir el bloqueo de WhatsApp
    y habilita las capacidades necesarias (localStorage, clipboard, WebGL).
    También inyecta JavaScript para suplantar APIs de detección de navegador.
    """

    def __init__(self, network_session=None):
        # network_session es construct-only en WebKit 6.0, debe pasarse
        # como keyword argument al constructor padre
        kwargs = {}
        if network_session is not None:
            kwargs["network_session"] = network_session
        super().__init__(**kwargs)
        self._notification_manager = None
        self._setup_settings()
        self._inject_browser_spoof()
        # Manejar solicitudes de permisos (micrófono, cámara, notificaciones)
        self.connect("permission-request", self._on_permission_request)
        # Notificaciones nativas: WhatsApp Web usa la Notifications API del
        # navegador. WebKit emite show-notification cuando eso ocurre.
        self.connect("show-notification", self._on_show_notification)

    def _setup_settings(self):
        """Configura los ajustes del WebView para WhatsApp Web."""
        settings = GObject.new(
            WebKit.Settings,
            user_agent=CHROME_USER_AGENT,
            enable_html5_local_storage=True,
            enable_javascript=True,
            enable_webgl=True,
            javascript_can_access_clipboard=True,
            allow_file_access_from_file_urls=False,
            enable_write_console_messages_to_stdout=False,
            # ── Media ──────────────────────────────────────────────────────
            # Permite que los audios y videos comiencen sin gesto del usuario.
            # Sin esto, las notas de voz y videos de WhatsApp no se reproducen.
            media_playback_requires_user_gesture=False,
            # Habilita acceso a micrófono y cámara (necesario para llamadas).
            enable_media_stream=True,
            # Habilita la Encrypted Media Extension (EME) para contenido protegido.
            enable_encrypted_media=True,
            # ── Rendering ─────────────────────────────────────────────────
            # Deshabilita la aceleración GPU en el compositor de capas de WebKit.
            # Algunos drivers Mesa/Wayland dentro del sandbox de Flatpak producen
            # artefactos visuales (bordes pixelados en emojis de reacciones,
            # glitches en transparencias). Esto NO afecta a WebGL (el contenido
            # multimedia de WhatsApp sigue usando GPU); solo cambia cómo WebKit
            # compone sus propias capas internas.
            hardware_acceleration_policy=WebKit.HardwareAccelerationPolicy.NEVER,
        )
        self.set_settings(settings)

    def _inject_browser_spoof(self):
        """Inyecta JS temprano para suplantar APIs de detección de navegador.

        WhatsApp Web usa múltiples métodos para detectar el navegador:
        - navigator.userAgent (cabecera HTTP + JS)
        - navigator.vendor (debe ser 'Google Inc.' en Chrome)
        - window.chrome (objeto exclusivo de Chrome)
        - navigator.plugins (Chrome expone plugins específicos)

        Este script se ejecuta en DOCUMENT_START, antes que cualquier
        JavaScript de la página, para evitar la detección.
        """
        spoof_script = """
        (function() {
            // Suplantar navigator.userAgent
            const chromeUA = '%s';
            Object.defineProperty(navigator, 'userAgent', {
                get: function() { return chromeUA; },
                configurable: true
            });
            Object.defineProperty(navigator, 'appVersion', {
                get: function() { return chromeUA.replace('Mozilla/', ''); },
                configurable: true
            });

            // Suplantar navigator.vendor
            Object.defineProperty(navigator, 'vendor', {
                get: function() { return 'Google Inc.'; },
                configurable: true
            });

            // Suplantar navigator.platform
            Object.defineProperty(navigator, 'platform', {
                get: function() { return 'Linux x86_64'; },
                configurable: true
            });

            // Agregar window.chrome (exclusivo de Chrome)
            if (!window.chrome) {
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
            }

            // Suplantar navigator.plugins.length > 0
            if (!navigator.plugins || navigator.plugins.length === 0) {
                Object.defineProperty(navigator, 'plugins', {
                    get: function() {
                        return {
                            0: { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                            1: { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                            2: { name: 'Native Client', filename: 'internal-nacl-plugin' },
                            length: 3,
                            item: function(i) { return this[i]; },
                            namedItem: function(n) { return this[0]; },
                            refresh: function() {}
                        };
                    },
                    configurable: true
                });
            }

            // Suplantar navigator.webdriver (Chrome no expone esto)
            Object.defineProperty(navigator, 'webdriver', {
                get: function() { return false; },
                configurable: true
            });

            // Suplantar navigator.languages
            Object.defineProperty(navigator, 'languages', {
                get: function() { return ['es-ES', 'es', 'en-US', 'en']; },
                configurable: true
            });

            // ── Notifications API ──────────────────────────────────────────
            // WhatsApp Web comprueba Notification.permission al arrancar.
            // Si no es 'granted' deja de usar la API y no llama nunca a
            // new Notification(), por lo que WebKit nunca emite show-notification.
            // Sobreescribimos la clase para que el permiso siempre sea 'granted'
            // y requestPermission() resuelva de forma inmediata.
            if (typeof Notification !== 'undefined') {
                // Guardar el constructor original por si se necesita internamente
                const _OriginalNotification = Notification;

                // Redefinir la clase Notification
                class PatchedNotification extends _OriginalNotification {
                    constructor(title, options) {
                        super(title, options);
                    }
                }

                // Propiedad estática: permission = 'granted'
                Object.defineProperty(PatchedNotification, 'permission', {
                    get: function() { return 'granted'; },
                    configurable: true
                });

                // requestPermission siempre resuelve con 'granted'
                PatchedNotification.requestPermission = function() {
                    return Promise.resolve('granted');
                };

                // Reemplazar el constructor global
                try {
                    Object.defineProperty(window, 'Notification', {
                        value: PatchedNotification,
                        writable: true,
                        configurable: true
                    });
                } catch(e) {
                    window.Notification = PatchedNotification;
                }
            }
        })();
        """ % CHROME_USER_AGENT

        user_content = self.get_user_content_manager()
        user_script = WebKit.UserScript.new(
            spoof_script,
            WebKit.UserContentInjectedFrames.ALL_FRAMES,
            WebKit.UserScriptInjectionTime.START,
        )
        user_content.add_script(user_script)

    # ── Notificaciones nativas ───────────────────────────────────────────

    def set_notification_manager(self, manager):
        """Registra el NotificationManager que procesará las notificaciones.

        Debe llamarse desde MainWindow después de crear ambos objetos.
        """
        self._notification_manager = manager

    def _on_show_notification(self, webview, notification) -> bool:
        """Callback de la señal show-notification de WebKit.

        Se dispara cuando WhatsApp Web llama a ``new Notification(title, opts)``.
        Delegamos al NotificationManager y retornamos True para indicarle a
        WebKit que nosotros manejamos la notificación (no debe intentarlo él).
        """
        if self._notification_manager is not None:
            return self._notification_manager.handle_webkit_notification(notification)
        return False

    # ── Permisos ──────────────────────────────────────────────────────────

    def _on_permission_request(
        self, webview: "WhatsAppWebView", request: WebKit.PermissionRequest
    ) -> bool:
        """Maneja solicitudes de permisos de la página web.

        WhatsApp Web solicita permisos para:
        - Notificaciones del escritorio
        - Micrófono (llamadas de voz)
        - Cámara (videollamadas)

        Los permisos de notificación se conceden automáticamente.
        Los de micrófono/cámara muestran un diálogo de confirmación.
        """
        # Notificaciones: conceder automáticamente (ya las manejamos nosotros)
        if isinstance(request, WebKit.NotificationPermissionRequest):
            request.allow()
            return True

        # Micrófono y/o cámara: preguntar al usuario
        if isinstance(
            request,
            (WebKit.UserMediaPermissionRequest, WebKit.DeviceInfoPermissionRequest),
        ):
            self._ask_media_permission(request)
            return True

        # Cualquier otro permiso: denegar por defecto
        request.deny()
        return True

    def _ask_media_permission(self, request: WebKit.PermissionRequest):
        """Muestra un diálogo pidiendo confirmación para micrófono/cámara."""
        is_video = (
            isinstance(request, WebKit.UserMediaPermissionRequest)
            and request.get_property("is-for-video-device")
        )
        device_label = "cámara y micrófono" if is_video else "micrófono"

        dialog = Gtk.AlertDialog()
        dialog.set_message(f"WhatsApp solicita acceso al {device_label}")
        dialog.set_detail(
            f"¿Deseas permitir que WhatsApp use el {device_label} de tu equipo?"
        )
        dialog.set_buttons(["Permitir", "Denegar"])
        dialog.set_default_button(0)
        dialog.set_cancel_button(1)
        dialog.choose(
            self.get_root(),
            None,
            self._on_media_permission_response,
            request,
        )

    def _on_media_permission_response(self, dialog, result, request):
        """Concede o deniega el permiso según la respuesta del usuario."""
        try:
            button = dialog.choose_finish(result)
            if button == 0:
                request.allow()
            else:
                request.deny()
        except Exception:
            request.deny()

    def load_whatsapp(self):
        """Carga WhatsApp Web."""
        self.load_uri(WHATSAPP_URL)

    def inject_css(self, css_content: str):
        """Inyecta CSS personalizado en la página."""
        user_content = self.get_user_content_manager()
        style_sheet = WebKit.UserStyleSheet.new(
            css_content,
            WebKit.UserContentInjectedFrames.ALL_FRAMES,
            WebKit.UserStyleLevel.USER,
        )
        user_content.add_style_sheet(style_sheet)

    def inject_javascript(self, js_code: str):
        """Inyecta JavaScript en la página (al final de la carga)."""
        user_content = self.get_user_content_manager()
        user_script = WebKit.UserScript.new(
            js_code,
            WebKit.UserContentInjectedFrames.ALL_FRAMES,
            WebKit.UserScriptInjectionTime.END,
        )
        user_content.add_script(user_script)
