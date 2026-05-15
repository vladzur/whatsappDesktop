"""Aplicación principal de WhatsApp Desk."""

import sys
import signal
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, Gio, GLib  # noqa: E402

from whatsapp_desk.constants import APP_ID
from whatsapp_desk.config import ConfigManager
from whatsapp_desk.webview_manager import WebViewManager


class WhatsAppDeskApplication(Gtk.Application):
    """Aplicación GTK4 de escritorio para WhatsApp Web.

    Gestiona el ciclo de vida, single-instance vía D-Bus,
    y la creación de la ventana principal.
    """

    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self._config = None
        self._webview_manager = None
        self._window = None

        # Opciones de línea de comandos
        self.add_main_option(
            "background",
            ord("b"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Iniciar minimizado en la bandeja del sistema",
            None,
        )

    @property
    def config(self) -> ConfigManager:
        return self._config

    @property
    def webview_manager(self) -> WebViewManager:
        return self._webview_manager

    def do_startup(self):
        """Inicializa servicios antes de crear ventanas."""
        Gtk.Application.do_startup(self)
        self._config = ConfigManager()
        self._webview_manager = WebViewManager()

        # Manejar SIGINT limpiamente
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    def do_activate(self):
        """Crea o restaura la ventana principal."""
        # Importación diferida para evitar dependencias circulares
        from whatsapp_desk.main_window import MainWindow

        if self._window is None:
            self._window = MainWindow(self)
        self._window.present()

    def do_command_line(self, command_line):
        """Procesa argumentos de línea de comandos."""
        options = command_line.get_options_dict()

        self.activate()

        if options.contains("background"):
            # Iniciar en segundo plano (solo bandeja)
            if self._window is not None:
                self._window.hide_to_tray()

        return 0

    def do_shutdown(self):
        """Limpieza al cerrar la aplicación."""
        if self._window is not None:
            self._window.save_geometry()
        Gtk.Application.do_shutdown(self)


def main():
    """Punto de entrada principal de la aplicación."""
    app = WhatsAppDeskApplication()
    return app.run(sys.argv)
