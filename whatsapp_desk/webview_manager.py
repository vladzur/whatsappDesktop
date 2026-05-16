"""Gestión de sesión persistente para WebKit."""

import os
import shutil
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import GObject, WebKit  # noqa: E402

from whatsapp_desk.constants import DATA_HOME


class WebViewManager:
    """Crea y administra la sesión de red persistente de WebKit."""

    def __init__(self, data_home=None):
        if data_home is None:
            data_home = DATA_HOME
        self._data_dir = os.path.join(data_home, "webkit-data")
        self._cache_dir = os.path.join(data_home, "webkit-cache")
        self._network_session = None
        self._ensure_directories()

    def _ensure_directories(self):
        """Crea los directorios de datos si no existen."""
        os.makedirs(self._data_dir, exist_ok=True)
        os.makedirs(self._cache_dir, exist_ok=True)

    def get_network_session(self) -> WebKit.NetworkSession:
        """Retorna una NetworkSession con persistencia en disco.

        La sesión se crea una sola vez y se reutiliza en llamadas sucesivas.
        data_directory y cache_directory son construct-only en WebKit 6.0,
        por lo que deben pasarse durante la construcción con GObject.new().
        """
        if self._network_session is None:
            self._ensure_directories()
            self._network_session = GObject.new(
                WebKit.NetworkSession,
                data_directory=self._data_dir,
                cache_directory=self._cache_dir,
                is_ephemeral=False,
            )
        return self._network_session

    def clear_session(self):
        """Elimina todos los datos de sesión (cookies, localStorage, caché)."""
        # Eliminar la sesión de red actual — los directorios se recrean
        # al llamar get_network_session() de nuevo.
        self._network_session = None
        for d in (self._data_dir, self._cache_dir):
            if os.path.exists(d):
                shutil.rmtree(d)
        self._ensure_directories()
