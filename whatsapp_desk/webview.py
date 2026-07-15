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
        self._inject_notification_fallback()
        self._inject_audio_mute()
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
            // Si no es 'granted' deja de usar la API y nunca llama a
            // new Notification(), por lo que WebKit nunca emite show-notification.
            //
            // ESTRATEGIA: Parchear las propiedades estáticas del constructor
            // original SIN reemplazarlo con una subclase.  Así WebKit sigue
            // emitiendo show-notification cuando WhatsApp crea notificaciones.
            if (typeof Notification !== 'undefined') {
                // --- permission getter (estrategia principal) ---
                // Intentamos redefinir el descriptor de permission directamente
                // en el constructor original.  Esto fuerza 'granted' sin
                // tocar el constructor, por lo que show-notification se emite.
                try {
                    var _permDesc = Object.getOwnPropertyDescriptor(
                        Notification, 'permission'
                    );
                    if (_permDesc && _permDesc.configurable !== false) {
                        Object.defineProperty(Notification, 'permission', {
                            get: function() { return 'granted'; },
                            configurable: true
                        });
                    } else {
                        // permission no es configurable.  Creamos un wrapper
                        // que devuelve instancias reales de Notification
                        // (no subclases) para que show-notification se emita.
                        throw new Error('permission no configurable');
                    }
                } catch (_e1) {
                    // --- wrapper (estrategia de respaldo) ---
                    // El wrapper retorna instancias reales vía new _OrigN(),
                    // por lo que WebKit emite show-notification correctamente.
                    try {
                        var _OrigN = window.Notification;
                        var _WrapN = function(title, options) {
                            return new _OrigN(title, options);
                        };
                        _WrapN.prototype = _OrigN.prototype;
                        Object.defineProperty(_WrapN, 'permission', {
                            get: function() { return 'granted'; },
                            configurable: true
                        });
                        _WrapN.requestPermission = function() {
                            return Promise.resolve('granted');
                        };
                        try {
                            Object.defineProperty(window, 'Notification', {
                                value: _WrapN, writable: true, configurable: true
                            });
                        } catch (_ignored) {
                            window.Notification = _WrapN;
                        }
                    } catch (_e2) {}
                }

                // --- requestPermission ---
                // Siempre intentamos parchear requestPermission en el
                // constructor, tanto si usamos la estrategia principal como
                // la de respaldo.
                try {
                    Notification.requestPermission = function() {
                        return Promise.resolve('granted');
                    };
                } catch (_e3) {}
            }

            // ── Permissions API ──────────────────────────────────────────
            // WhatsApp Web moderno también verifica el permiso de notificación
            // mediante navigator.permissions.query({name:'notifications'}).
            if (navigator.permissions && navigator.permissions.query) {
                var _origQuery = navigator.permissions.query.bind(
                    navigator.permissions
                );
                navigator.permissions.query = function(desc) {
                    if (desc && desc.name === 'notifications') {
                        return Promise.resolve({
                            state: 'granted', onchange: null
                        });
                    }
                    return _origQuery(desc);
                };
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

    def _inject_notification_fallback(self):
        """Reaplica el parche de Notification y Permissions API en DOCUMENT_END.

        En WebKitGTK 6.0, las bindings de JavaScript pueden no estar
        completamente inicializadas en DOCUMENT_START.  Esta inyección de
        respaldo garantiza que Notification.permission esté forzado a
        'granted' aunque el parche de DOCUMENT_START no haya funcionado.
        """
        fallback_script = """
        (function() {
            // Reaplicar parche de Notification.permission si no está activo
            if (typeof Notification !== 'undefined' &&
                Notification.permission !== 'granted') {
                try {
                    var permDesc = Object.getOwnPropertyDescriptor(
                        Notification, 'permission'
                    );
                    if (permDesc && permDesc.configurable !== false) {
                        Object.defineProperty(Notification, 'permission', {
                            get: function() { return 'granted'; },
                            configurable: true
                        });
                    }
                } catch (_e) {}
                try {
                    Notification.requestPermission = function() {
                        return Promise.resolve('granted');
                    };
                } catch (_e) {}
            }

            // Reaplicar parche de Permissions API
            if (navigator.permissions && navigator.permissions.query) {
                var _origQ = navigator.permissions.query.bind(
                    navigator.permissions
                );
                navigator.permissions.query = function(desc) {
                    if (desc && desc.name === 'notifications') {
                        return Promise.resolve({
                            state: 'granted', onchange: null
                        });
                    }
                    return _origQ(desc);
                };
            }
        })();
        """

        user_content = self.get_user_content_manager()
        user_script = WebKit.UserScript.new(
            fallback_script,
            WebKit.UserContentInjectedFrames.ALL_FRAMES,
            WebKit.UserScriptInjectionTime.END,
        )
        user_content.add_script(user_script)

    def _inject_audio_mute(self):
        """Suprime los sonidos de notificación de WhatsApp Web.

        WhatsApp reproduce sonidos cortos al recibir mensajes.  GNOME detecta
        esa reproducción vía PipeWire y muestra un «reproductor multimedia»
        fantasma en el área de notificaciones en lugar de la burbuja real.

        Esta inyección silencia los elementos <audio> que coinciden con
        patrones de URL típicos de sonidos de notificación.  Las notas de
        voz y las llamadas (WebRTC) NO se ven afectadas porque usan
        mecanismos diferentes.
        """
        audio_mute_script = """
        (function() {
            // Interceptar HTMLAudioElement.play() para silenciar sonidos
            // de notificación por patrón de URL.
            var _origPlay = HTMLAudioElement.prototype.play;
            HTMLAudioElement.prototype.play = function() {
                var src = (this.src || '').toLowerCase();
                var isNotif = (
                    /notification|notif|alert|new_msg|msg_received/i.test(src)
                );
                if (isNotif) {
                    try { this.volume = 0; } catch (_e) {}
                }
                return _origPlay.call(this).catch(function() {});
            };

            // Interceptar el constructor Audio() para silenciar por URL
            if (typeof Audio !== 'undefined') {
                var _OrigAudio = Audio;
                window.Audio = function(src) {
                    var instance = new _OrigAudio(src);
                    if (src && /notification|notif/i.test(src)) {
                        try { instance.volume = 0; } catch (_e) {}
                    }
                    return instance;
                };
                window.Audio.prototype = _OrigAudio.prototype;
            }
        })();
        """

        user_content = self.get_user_content_manager()
        user_script = WebKit.UserScript.new(
            audio_mute_script,
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
