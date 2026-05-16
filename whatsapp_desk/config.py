"""Gestión de configuración persistente en JSON."""

import json
import os
from whatsapp_desk.constants import CONFIG_HOME, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT

DEFAULT_CONFIG = {
    "dark_mode": False,
    "notifications_enabled": True,
    "close_to_tray": True,
    "start_in_background": False,
    "zoom_level": 1.0,
    "window_width": DEFAULT_WINDOW_WIDTH,
    "window_height": DEFAULT_WINDOW_HEIGHT,
    "window_maximized": False,
}


class ConfigManager:
    """Administra la configuración de la aplicación en un archivo JSON."""

    def __init__(self, config_dir=None):
        if config_dir is None:
            config_dir = CONFIG_HOME
        self._config_dir = config_dir
        self._file_path = os.path.join(self._config_dir, "settings.json")
        self._data = {}
        self._load()

    def _load(self):
        """Carga la configuración desde disco o usa los valores por defecto."""
        os.makedirs(self._config_dir, exist_ok=True)
        try:
            with open(self._file_path, "r") as f:
                self._data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._data = {}
        # Aplicar valores por defecto para claves faltantes
        for key, value in DEFAULT_CONFIG.items():
            if key not in self._data:
                self._data[key] = value

    def _save(self):
        """Guarda la configuración a disco."""
        os.makedirs(self._config_dir, exist_ok=True)
        with open(self._file_path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key, default=None):
        """Obtiene un valor de configuración."""
        return self._data.get(key, default or DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        """Establece un valor de configuración y lo persiste."""
        self._data[key] = value
        self._save()

    def toggle(self, key):
        """Alterna un valor booleano de configuración."""
        current = self.get(key, False)
        self.set(key, not current)
        return not current
