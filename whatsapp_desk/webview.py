"""WebView de WhatsApp con configuración personalizada."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import GObject, WebKit  # noqa: E402

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
        self._setup_settings()
        self._inject_browser_spoof()

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
        })();
        """ % CHROME_USER_AGENT

        user_content = self.get_user_content_manager()
        user_script = WebKit.UserScript.new(
            spoof_script,
            WebKit.UserContentInjectedFrames.ALL_FRAMES,
            WebKit.UserScriptInjectionTime.START,
        )
        user_content.add_script(user_script)

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
