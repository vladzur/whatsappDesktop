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
    """

    def __init__(self, network_session=None):
        super().__init__()
        self._setup_settings()
        if network_session is not None:
            self.set_property("network-session", network_session)

    def _setup_settings(self):
        """Configura los ajustes del WebView para WhatsApp Web."""
        settings = self.get_settings()
        # Evadir bloqueo de User-Agent
        settings.set_property("user-agent", CHROME_USER_AGENT)
        # Capacidades necesarias para WhatsApp Web
        settings.set_property("enable-html5-local-storage", True)
        settings.set_property("enable-javascript", True)
        settings.set_property("enable-webgl", True)
        # Permitir pegado desde portapapeles (necesario para enviar imágenes)
        settings.set_property("javascript-can-access-clipboard", True)

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
        """Inyecta JavaScript en la página."""
        user_content = self.get_user_content_manager()
        user_script = WebKit.UserScript.new(
            js_code,
            WebKit.UserContentInjectedFrames.ALL_FRAMES,
            WebKit.UserScriptInjectionTime.END,
        )
        user_content.add_script(user_script)
