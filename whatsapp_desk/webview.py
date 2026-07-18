"""WebView de WhatsApp con configuración personalizada."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import GObject, Gtk, WebKit  # noqa: E402

from whatsapp_desk.constants import WHATSAPP_URL
from whatsapp_desk.resources.ua_chrome import CHROME_USER_AGENT


class _BridgeNotification:
    """Notificación sintética que emula la interfaz de WebKit.Notification.

    Se usa cuando el bridge JS→Python vía ``window.webkit.messageHandlers``
    recibe los datos de una notificación.  WebKitGTK 6.0 no emite la señal
    ``show-notification``, así que este objeto reemplaza al
    ``WebKit.Notification`` que el ``NotificationManager`` espera recibir.
    """

    def __init__(self, title: str, body: str):
        self._title = title
        self._body = body

    def get_title(self) -> str:
        return self._title

    def get_body(self) -> str:
        return self._body


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
        self._register_script_message_handler()
        self._inject_browser_spoof()
        self._inject_notification_fallback()
        self._inject_audio_mute()
        # Manejar solicitudes de permisos (micrófono, cámara, notificaciones)
        self.connect("permission-request", self._on_permission_request)
        # Notificaciones nativas (señal WebKit, puede no emitirse en 6.0)
        self.connect("show-notification", self._on_show_notification)

    def _register_script_message_handler(self):
        """Registra un message handler JS→Python para notificaciones.

        WebKitGTK 6.0 no emite la señal ``show-notification`` para
        notificaciones creadas vía JavaScript.  En su lugar, usamos
        ``window.webkit.messageHandlers.notify.postMessage()`` para
        enviar los datos de la notificación desde JS a Python.
        """
        self._user_content = self.get_user_content_manager()
        try:
            # Registrar el handler «notify» para que JS pueda llamar a
            # window.webkit.messageHandlers.notify.postMessage(json)
            try:
                self._user_content.register_script_message_handler("notify")
            except TypeError:
                # WebKitGTK 2.40+ requiere el parámetro world_name
                self._user_content.register_script_message_handler(
                    "notify", None
                )
            self._user_content.connect(
                "script-message-received::notify",
                self._on_notify_message,
            )
        except Exception as exc:
            print(f"[WebView] Error al registrar message handler: {exc}")

    def _on_notify_message(self, manager, js_result):
        """Callback del message handler JS→Python para notificaciones.

        Recibe un JSON con ``title`` y ``body`` desde JavaScript y lo
        convierte en una notificación de escritorio real vía libnotify.
        """
        import json
        try:
            raw = js_result.to_string()
            data = json.loads(raw)
            title = data.get("title", "WhatsApp Desk")
            body = data.get("body", "Nuevo mensaje")

            if self._notification_manager is not None:
                # El NotificationManager espera un objeto con get_title()
                # y get_body().  Creamos una notificación sintética ya que
                # WebKitGTK 6.0 no emite show-notification.
                notif = _BridgeNotification(title, body)
                self._notification_manager.handle_webkit_notification(notif)
        except Exception as exc:
            print(f"[WebView] Error al procesar mensaje JS: {exc}")

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
            console.log('[WhatsAppDesk] DOC_START: typeof Notification = ' + typeof Notification);
            if (typeof Notification !== 'undefined') {
                console.log('[WhatsAppDesk] DOC_START: perm original = ' + Notification.permission);
                // --- permission getter (estrategia principal) ---
                // Intentamos redefinir el descriptor de permission directamente
                // en el constructor original.  Esto fuerza 'granted' sin
                // tocar el constructor, por lo que show-notification se emite.
                try {
                    var _permDesc = Object.getOwnPropertyDescriptor(
                        Notification, 'permission'
                    );
                    if (_permDesc && _permDesc.configurable !== false) {
                        console.log('[WhatsAppDesk] DOC_START: parchando permission directamente');
                        Object.defineProperty(Notification, 'permission', {
                            get: function() { return 'granted'; },
                            configurable: true
                        });
                        console.log('[WhatsAppDesk] DOC_START: perm despues de parche = ' + Notification.permission);
                    } else {
                        console.log('[WhatsAppDesk] DOC_START: permission NO configurable, usando wrapper');
                        // permission no es configurable.  Creamos un wrapper
                        // que devuelve instancias reales de Notification
                        // (no subclases) para que show-notification se emita.
                        throw new Error('permission no configurable');
                    }
                } catch (_e1) {
                    console.log('[WhatsAppDesk] DOC_START: estrategia 1 fallo, usando wrapper. Error: ' + _e1);
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
                            console.log('[WhatsAppDesk] DOC_START: wrapper instalado con defineProperty');
                        } catch (_ignored) {
                            window.Notification = _WrapN;
                            console.log('[WhatsAppDesk] DOC_START: wrapper instalado con asignacion directa');
                        }
                        console.log('[WhatsAppDesk] DOC_START: perm despues de wrapper = ' + Notification.permission);
                    } catch (_e2) {
                        console.log('[WhatsAppDesk] DOC_START: wrapper tambien fallo: ' + _e2);
                    }
                }

                // --- Bridge JS->Python via message handlers ---
                // WebKitGTK 6.0 NO emite la señal show-notification para
                // notificaciones creadas por JS.  En su lugar, interceptamos
                // el constructor Notification para enviar los datos a Python
                // via window.webkit.messageHandlers.notify.postMessage().
                if (window.webkit && window.webkit.messageHandlers &&
                    window.webkit.messageHandlers.notify) {
                    console.log('[WhatsAppDesk] DOC_START: instalando bridge message handler');
                    var _NotifyOrig = Notification;
                    var _NotifyBridge = function(title, options) {
                        try {
                            var body = (options && options.body) ? options.body : '';
                            window.webkit.messageHandlers.notify.postMessage(
                                JSON.stringify({title: title, body: body})
                            );
                            console.log('[WhatsAppDesk] Bridge: notificacion enviada a Python');
                        } catch(_bridgeErr) {
                            console.log('[WhatsAppDesk] Bridge: error postMessage: ' + _bridgeErr);
                        }
                        // Crear la notificación real para que WhatsApp no falle
                        return new _NotifyOrig(title, options);
                    };
                    _NotifyBridge.prototype = _NotifyOrig.prototype;
                    _NotifyBridge.permission = 'granted';
                    _NotifyBridge.requestPermission = function() {
                        return Promise.resolve('granted');
                    };
                    // Reemplazar window.Notification con el bridge
                    try {
                        Object.defineProperty(window, 'Notification', {
                            value: _NotifyBridge, writable: true, configurable: true
                        });
                    } catch(_bri2) {
                        window.Notification = _NotifyBridge;
                    }
                    console.log('[WhatsAppDesk] DOC_START: bridge instalado, perm=' + Notification.permission);
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
            console.log('[WhatsAppDesk] DOC_END: reaplicando parche');
            // Reaplicar parche de Notification.permission si no está activo
            if (typeof Notification !== 'undefined' &&
                Notification.permission !== 'granted') {
                console.log('[WhatsAppDesk] DOC_END: permission aun no es granted, reaplicando...');
                // Intentar parche directo primero
                var parched = false;
                try {
                    var permDesc = Object.getOwnPropertyDescriptor(
                        Notification, 'permission'
                    );
                    if (permDesc && permDesc.configurable !== false) {
                        Object.defineProperty(Notification, 'permission', {
                            get: function() { return 'granted'; },
                            configurable: true
                        });
                        parched = true;
                        console.log('[WhatsAppDesk] DOC_END: parche directo aplicado');
                    }
                } catch (_e) {
                    console.log('[WhatsAppDesk] DOC_END: parche directo fallo: ' + _e);
                }
                // Si el parche directo no funcionó, intentar wrapper
                if (!parched) {
                    try {
                        var _OrigN2 = window.Notification;
                        var _WrapN2 = function(title, options) {
                            return new _OrigN2(title, options);
                        };
                        _WrapN2.prototype = _OrigN2.prototype;
                        Object.defineProperty(_WrapN2, 'permission', {
                            get: function() { return 'granted'; },
                            configurable: true
                        });
                        _WrapN2.requestPermission = function() {
                            return Promise.resolve('granted');
                        };
                        try {
                            Object.defineProperty(window, 'Notification', {
                                value: _WrapN2, writable: true, configurable: true
                            });
                        } catch (_ignored2) {
                            window.Notification = _WrapN2;
                        }
                        console.log('[WhatsAppDesk] DOC_END: wrapper aplicado');
                    } catch (_e2) {
                        console.log('[WhatsAppDesk] DOC_END: wrapper tambien fallo: ' + _e2);
                    }
                }
                try {
                    Notification.requestPermission = function() {
                        return Promise.resolve('granted');
                    };
                } catch (_e) {}
                console.log('[WhatsAppDesk] DOC_END: permission final = ' + Notification.permission);
            } else if (typeof Notification !== 'undefined') {
                console.log('[WhatsAppDesk] DOC_END: permission ya es granted, OK');
            }

            // Reaplicar parche de Permissions API
            if (navigator.permissions && navigator.permissions.query) {
                var _origQf = navigator.permissions.query.bind(
                    navigator.permissions
                );
                navigator.permissions.query = function(desc) {
                    if (desc && desc.name === 'notifications') {
                        return Promise.resolve({
                            state: 'granted', onchange: null
                        });
                    }
                    return _origQf(desc);
                };
            }

            // Instalar bridge JS->Python via message handlers
            // (puede que en DOC_START el handler no estuviera listo)
            if (window.webkit && window.webkit.messageHandlers &&
                window.webkit.messageHandlers.notify &&
                typeof Notification !== 'undefined') {
                console.log('[WhatsAppDesk] DOC_END: instalando bridge message handler');
                var _NO = Notification;
                var _NB = function(title, options) {
                    try {
                        var b = (options && options.body) ? options.body : '';
                        window.webkit.messageHandlers.notify.postMessage(
                            JSON.stringify({title: title, body: b})
                        );
                    } catch(_be) {}
                    return new _NO(title, options);
                };
                _NB.prototype = _NO.prototype;
                _NB.permission = 'granted';
                _NB.requestPermission = function() { return Promise.resolve('granted'); };
                try {
                    Object.defineProperty(window, 'Notification', {
                        value: _NB, writable: true, configurable: true
                    });
                } catch(_bi) {
                    window.Notification = _NB;
                }
                console.log('[WhatsAppDesk] DOC_END: bridge instalado');
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
        """Suprime los sonidos de notificación de WhatsApp Web y limpia MPRIS.

        WhatsApp reproduce sonidos cortos al recibir mensajes.  GNOME detecta
        esa reproducción vía PipeWire/MPRIS y muestra un «reproductor
        multimedia» fantasma en el área de notificaciones.

        Estrategia:
        1. Para sonidos de notificación (identificados por patrón de URL):
           bloqueamos completamente play() para que WebKitGTK nunca cree
           una entrada MPRIS.  No basta con silenciar (volume=0) porque el
           elemento sigue en estado «playing» y MPRIS lo registra igual.

        2. Para todos los elementos <audio> y <video> (notas de voz,
           llamadas): agregamos un listener «ended» que limpia el src del
           elemento para forzar a WebKitGTK a liberar la entrada MPRIS
           inmediatamente al terminar la reproducción, evitando que quede
           un reproductor fantasma en el área de notificaciones de GNOME.
        """
        audio_mute_script = """
        (function() {
            // ── Bloqueo de sonidos de notificación ────────────────────────
            // Interceptamos HTMLAudioElement.play() para BLOQUEAR sonidos
            // de notificación (no solo silenciarlos).  Esto evita que
            // WebKitGTK cree una entrada MPRIS para estos sonidos.
            var _origAudioPlay = HTMLAudioElement.prototype.play;
            HTMLAudioElement.prototype.play = function() {
                var src = (this.src || '').toLowerCase();
                var isNotif = (
                    /notification|notif|alert|new_msg|msg_received/i.test(src)
                );
                if (isNotif) {
                    // Bloquear completamente: no llamar al play original.
                    // Retornamos una promesa resuelta para que el caller
                    // no reciba errores.
                    return Promise.resolve();
                }
                return _origAudioPlay.call(this).catch(function() {});
            };

            // Interceptar el constructor Audio() para bloquear por URL
            if (typeof Audio !== 'undefined') {
                var _OrigAudio = Audio;
                window.Audio = function(src) {
                    var instance = new _OrigAudio(src);
                    if (src && /notification|notif/i.test(src)) {
                        // Parchear play() en esta instancia específica
                        // para que nunca inicie reproducción
                        instance.play = function() {
                            return Promise.resolve();
                        };
                    }
                    return instance;
                };
                window.Audio.prototype = _OrigAudio.prototype;
            }

            // ── Limpieza MPRIS para notas de voz y videos ─────────────────
            // Al terminar cualquier reproducción de <audio> o <video>,
            // limpiamos el src para que WebKitGTK libere inmediatamente
            // la entrada MPRIS.  Esto evita que el reproductor multimedia
            // fantasma persista en el área de notificaciones de GNOME.
            function _addMediaCleanup(el) {
                if (!el || el._whatsappDeskCleanup) return;
                el._whatsappDeskCleanup = true;
                el.addEventListener('ended', function() {
                    // Pequeño retardo para asegurar que el evento 'ended'
                    // se haya procesado completamente antes de limpiar
                    setTimeout(function() {
                        try {
                            // Pausar explícitamente antes de limpiar src
                            // para notificar a WebKitGTK que la reproducción
                            // ha terminado realmente
                            el.pause();
                            // Limpiar src fuerza a WebKitGTK a liberar
                            // el pipeline de GStreamer y la entrada MPRIS
                            el.removeAttribute('src');
                            el.load();
                        } catch(_e) {}
                    }, 100);
                });
                // También limpiar en caso de error de carga
                el.addEventListener('error', function() {
                    setTimeout(function() {
                        try {
                            el.pause();
                            el.removeAttribute('src');
                            el.load();
                        } catch(_e) {}
                    }, 100);
                });
            }

            // Escanear elementos media ya existentes e iniciar observación
            function _scanAndObserve() {
                // Escanear elementos ya presentes
                var existing = document.querySelectorAll('audio, video');
                for (var i = 0; i < existing.length; i++) {
                    _addMediaCleanup(existing[i]);
                }

                // Observar elementos nuevos en el DOM
                if (window.MutationObserver && document.documentElement) {
                    var _observer = new MutationObserver(function(mutations) {
                        mutations.forEach(function(m) {
                            m.addedNodes.forEach(function(node) {
                                if (node.nodeType === 1) {
                                    if (node.tagName === 'AUDIO' ||
                                        node.tagName === 'VIDEO') {
                                        _addMediaCleanup(node);
                                    }
                                    if (node.querySelectorAll) {
                                        var media = node.querySelectorAll(
                                            'audio, video'
                                        );
                                        for (var i = 0; i < media.length; i++) {
                                            _addMediaCleanup(media[i]);
                                        }
                                    }
                                }
                            });
                        });
                    });
                    _observer.observe(document.documentElement, {
                        childList: true, subtree: true
                    });
                }
            }

            // Ejecutar cuando el DOM esté listo (en DOCUMENT_START
            // documentElement puede no existir aún)
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', _scanAndObserve);
            } else {
                _scanAndObserve();
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
