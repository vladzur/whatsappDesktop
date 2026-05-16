"""Aplicación principal de WhatsApp Desk."""

import os
import sys
import signal
import shutil
import subprocess
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, Gio, GLib  # noqa: E402

from whatsapp_desk.constants import APP_ID
from whatsapp_desk.config import ConfigManager
from whatsapp_desk.webview_manager import WebViewManager

# Ruta al icono SVG dentro del proyecto
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ICON_SRC = os.path.join(_PROJECT_ROOT, "whatsapp-desk.svg")

# Directorio de instalación del icono según XDG
_ICON_INSTALL_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "icons",
    "hicolor",
    "scalable",
    "apps",
)
_ICON_INSTALL_PATH = os.path.join(_ICON_INSTALL_DIR, "whatsapp-desk.svg")


def _ensure_icon_installed():
    """Copia el icono al directorio de iconos del usuario y actualiza caché."""
    if not os.path.isfile(_ICON_SRC):
        return False
    try:
        os.makedirs(_ICON_INSTALL_DIR, exist_ok=True)
        if not os.path.isfile(_ICON_INSTALL_PATH):
            shutil.copy2(_ICON_SRC, _ICON_INSTALL_PATH)
        # Actualizar caché de iconos GTK si la herramienta existe
        cache_dir = os.path.dirname(os.path.dirname(_ICON_INSTALL_DIR))
        subprocess.run(
            ["gtk-update-icon-cache", "-t", "-f", cache_dir],
            capture_output=True,
        )
        return True
    except OSError:
        return False


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

        # Instalar icono en el sistema para dock y bandeja
        _ensure_icon_installed()

        self._config = ConfigManager()
        self._webview_manager = WebViewManager()
        self._register_actions()

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

    def _register_actions(self):
        """Registra las acciones GAction de la aplicación."""
        # Acción para mostrar la ventana (desde la bandeja)
        show_action = Gio.SimpleAction.new("show-window", None)
        show_action.connect("activate", self._on_show_window)
        self.add_action(show_action)

        # Acción para limpiar la sesión (logout de WhatsApp)
        clear_action = Gio.SimpleAction.new("clear-session", None)
        clear_action.connect("activate", self._on_clear_session)
        self.add_action(clear_action)

        # Acción nueva ventana (mismo comportamiento que show)
        new_action = Gio.SimpleAction.new("new-window", None)
        new_action.connect("activate", self._on_show_window)
        self.add_action(new_action)

    def _on_show_window(self, action, param):
        """Muestra la ventana principal."""
        if self._window is not None:
            self._window.present()

    def _on_clear_session(self, action, param):
        """Limpia los datos de sesión de WhatsApp."""
        if self._window is not None:
            self._webview_manager.clear_session()
            self._window.replace_webview()


def main():
    """Punto de entrada principal de la aplicación."""
    app = WhatsAppDeskApplication()
    return app.run(sys.argv)
