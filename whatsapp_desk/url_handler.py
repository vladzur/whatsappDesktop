"""Manejo de enlaces externos — abre URLs fuera de WhatsApp en el navegador."""

import logging
from urllib.parse import urlparse
import gi

gi.require_version("WebKit", "6.0")
from gi.repository import Gio, GLib, WebKit  # noqa: E402

logger = logging.getLogger(__name__)


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

# MIME types que el WebView puede renderizar/reproducir sin descargar.
# NOTA: audio/* y video/* se incluyen porque WhatsApp puede navegar
# directamente a URLs de media. Si el codec no está instalado,
# is_mime_type_supported() devolverá False y se descargará igualmente.
_NAVIGABLE_MIME_PREFIXES = (
    "text/",
    "application/xhtml",
    "application/xml",
    "image/svg",
    "audio/",
    "video/",
)


class UrlHandler:
    """Intercepta solicitudes de navegación y redirige enlaces externos.

    Maneja dos tipos de decisiones de política:
    - NAVIGATION_ACTION: decide si la URL se abre en el WebView o externamente.
    - RESPONSE: decide si el contenido de una respuesta se muestra o descarga.
    """

    def __init__(self, webview: WebKit.WebView):
        self._webview = webview
        webview.connect("decide-policy", self._on_decide_policy)

    def _on_decide_policy(self, webview, decision, decision_type):
        """Enruta la decisión de política al manejador correcto."""
        if decision_type == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            return self._handle_navigation(decision)
        if decision_type == WebKit.PolicyDecisionType.RESPONSE:
            return self._handle_response(decision)
        return False

    # ── Navegación ────────────────────────────────────────────────────────

    def _handle_navigation(self, decision: WebKit.NavigationPolicyDecision) -> bool:
        """Abre URLs externas en el navegador del sistema."""
        nav_action = decision.get_navigation_action()
        request = nav_action.get_request()
        uri = request.get_uri()

        if self._is_whatsapp_url(uri):
            return False  # Permitir navegación dentro del WebView

        # Enlace externo: abrir en el navegador y bloquear navegación interna
        self._open_external(uri)
        decision.ignore()
        return True

    # ── Respuesta HTTP (descargas) ─────────────────────────────────────────

    def _handle_response(self, decision: WebKit.ResponsePolicyDecision) -> bool:
        """Decide si un recurso HTTP se muestra en el WebView o se descarga.

        WebKit emite RESPONSE después de recibir las cabeceras HTTP.
        Si el servidor indica Content-Disposition: attachment, o el MIME
        type no es navegable, delegamos la descarga al DownloadManager.
        """
        if not decision.is_mime_type_supported():
            # MIME type que el WebView no puede renderizar → descargar
            decision.download()
            return True

        response = decision.get_response()
        mime = (response.get_mime_type() or "").lower()

        # Forzar descarga para tipos binarios aunque el WebView "los soporte"
        if not any(mime.startswith(p) for p in _NAVIGABLE_MIME_PREFIXES):
            decision.download()
            return True

        return False  # Mostrar el contenido en el WebView

    # ── Utilidades ────────────────────────────────────────────────────────

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
        """Abre una URL en el navegador por defecto del sistema.

        Usa la variante asíncrona para que la llamada D-Bus al portal
        xdg-desktop-portal tenga tiempo de completarse dentro del sandbox
        de Flatpak. La versión síncrona puede retornar antes de que el
        portal haya procesado la solicitud, dejando el enlace sin abrir.
        """
        Gio.AppInfo.launch_default_for_uri_async(
            uri,
            None,   # AppLaunchContext
            None,   # Cancellable
            self._on_launch_finished,
            uri,    # user_data (para el log)
        )

    @staticmethod
    def _on_launch_finished(source, result, uri):
        """Callback de launch_default_for_uri_async — registra errores."""
        try:
            Gio.AppInfo.launch_default_for_uri_finish(result)
        except GLib.Error as exc:
            logger.warning("No se pudo abrir el enlace '%s': %s", uri, exc)

