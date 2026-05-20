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

from whatsapp_desk.constants import (
    APP_ID,
    IN_FLATPAK,
    ICON_DIR,
    ICON_SRC_DIR,
)
from whatsapp_desk.config import ConfigManager
from whatsapp_desk.webview_manager import WebViewManager

# Rutas de iconos derivadas de las constantes del módulo
_ICON_SRC = os.path.join(ICON_SRC_DIR, "whatsapp-desk.svg")
_ICON_SYMBOLIC_SRC = os.path.join(ICON_SRC_DIR, "whatsapp-desk-symbolic.svg")
_ICON_INSTALL_PATH = os.path.join(ICON_DIR, "whatsapp-desk.svg")
_ICON_SYMBOLIC_PATH = os.path.join(ICON_DIR, "whatsapp-desk-symbolic.svg")


def _ensure_icons_installed():
    """Copia los iconos al directorio XDG del usuario y actualiza caché.

    En Flatpak los iconos ya vienen preinstalados en /app/share/icons/,
    por lo que esta función es no-op en ese entorno.
    """
    if IN_FLATPAK:
        return True
    if not os.path.isfile(_ICON_SRC):
        return False
    try:
        os.makedirs(ICON_DIR, exist_ok=True)
        for src, dst in [
            (_ICON_SRC, _ICON_INSTALL_PATH),
            (_ICON_SYMBOLIC_SRC, _ICON_SYMBOLIC_PATH),
        ]:
            if os.path.isfile(src) and not os.path.isfile(dst):
                shutil.copy2(src, dst)
        # Actualizar caché de iconos GTK si la herramienta existe
        cache_dir = os.path.dirname(os.path.dirname(ICON_DIR))
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

        # Instalar iconos en el sistema para dock y bandeja
        _ensure_icons_installed()

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
            # Limpiar recursos D-Bus del icono de bandeja
            if self._window._tray is not None:
                self._window._tray.cleanup()
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

        # Acción quit — GTK4 NO la registra automáticamente como GAction.
        # Sin esto, el ítem "Salir" del menú y la bandeja no hacen nada.
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)

    def _on_show_window(self, action, param):
        """Muestra la ventana principal."""
        if self._window is not None:
            self._window.present()

    def _on_quit(self, action, param):
        """Cierra la aplicación completamente, ignorando close_to_tray."""
        if self._window is not None:
            self._window.save_geometry()
            # Forzar cierre real: desconectar el guard de close-request
            self._window.force_quit = True
        self.quit()

    def _on_clear_session(self, action, param):
        """Limpia los datos de sesión de WhatsApp."""
        if self._window is not None:
            self._webview_manager.clear_session()
            self._window.replace_webview()


def main():
    """Punto de entrada principal de la aplicación."""
    app = WhatsAppDeskApplication()
    return app.run(sys.argv)
