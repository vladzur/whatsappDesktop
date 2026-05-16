"""Manejo de enlaces externos — abre URLs fuera de WhatsApp en el navegador."""

from urllib.parse import urlparse
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gio, WebKit  # noqa: E402


# Dominios que pertenecen a WhatsApp y deben cargarse en el WebView
WHATSAPP_DOMAINS = {
    "web.whatsapp.com",
    "whatsapp.com",
    "www.whatsapp.com",
    "faq.whatsapp.com",
    "blog.whatsapp.com",
    "flows.whatsapp.net",
    "whatsapp.net",
    "www.whatsapp.net",
}


class UrlHandler:
    """Intercepta solicitudes de navegación y redirige enlaces externos."""

    def __init__(self, webview: WebKit.WebView):
        self._webview = webview
        # Conectar la señal decide-policy
        webview.connect("decide-policy", self._on_decide_policy)

    def _on_decide_policy(
        self, webview, decision, decision_type
    ):
        """Determina si una navegación debe ocurrir en el WebView o externamente."""
        if decision_type != WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            return False  # Permitir otros tipos de decisiones

        nav_action = decision.get_navigation_action()
        request = nav_action.get_request()
        uri = request.get_uri()

        if self._is_whatsapp_url(uri):
            return False  # Permitir navegación en el WebView

        # Enlace externo: abrir en navegador del sistema
        self._open_external(uri)
        decision.ignore()  # Bloquear navegación en el WebView
        return True

    def _is_whatsapp_url(self, uri: str) -> bool:
        """Determina si una URL pertenece al ecosistema de WhatsApp."""
        try:
            parsed = urlparse(uri)
            hostname = (parsed.hostname or "").lower()
            return (
                hostname in WHATSAPP_DOMAINS
                or hostname.endswith(".whatsapp.com")
                or hostname.endswith(".whatsapp.net")
            )
        except Exception:
            return False

    def _open_external(self, uri: str):
        """Abre una URL en el navegador por defecto del sistema."""
        try:
            Gio.AppInfo.launch_default_for_uri(uri)
        except Exception:
            pass  # Fallar silenciosamente si no se puede abrir
