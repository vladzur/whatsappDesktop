"""Gestión del modo oscuro para la aplicación y el WebView."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, WebKit  # noqa: E402


class DarkModeManager:
    """Administra el modo oscuro de la aplicación.

    Lee la preferencia del sistema GTK4 y la propaga al WebView.
    WebKit 6.0 detecta automáticamente prefers-color-scheme del
    tema GTK, por lo que WhatsApp Web cambia su tema solo.
    """

    def __init__(self, webview: WebKit.WebView, config):
        self._webview = webview
        self._config = config

        # Aplicar el modo oscuro guardado en la configuración
        self.apply()

    def apply(self):
        """Aplica la configuración de modo oscuro."""
        dark = self._config.get("dark_mode", False)
        self._set_gtk_dark_mode(dark)

    def toggle(self):
        """Alterna el modo oscuro y persiste la preferencia."""
        dark = self._config.toggle("dark_mode")
        self._set_gtk_dark_mode(dark)
        return dark

    def _set_gtk_dark_mode(self, dark: bool):
        """Establece la preferencia de tema oscuro en GTK4.

        WebKit 6.0 hereda automáticamente la media query CSS
        prefers-color-scheme del tema GTK, por lo que no se
        necesita inyección CSS adicional para el tema base.
        """
        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings is not None:
            gtk_settings.set_property(
                "gtk-application-prefer-dark-theme", dark
            )
