"""Constantes globales de la aplicación."""

import os

# Identificador único D-Bus para single-instance
APP_ID = "com.vladzur.WhatsAppDesk"

# URL de WhatsApp Web
WHATSAPP_URL = "https://web.whatsapp.com/"

# Detectar si se ejecuta dentro de un sandbox Flatpak
IN_FLATPAK = os.path.isdir("/app") or "FLATPAK_ID" in os.environ

# Ruta raíz del proyecto (fuera del paquete)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directorios de datos de la aplicación
DATA_HOME = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "whatsapp-desk",
)
CONFIG_HOME = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "whatsapp-desk",
)

# Rutas de iconos — se adaptan al entorno (Flatpak vs desarrollo/instalación local)
if IN_FLATPAK:
    # En Flatpak los iconos se preinstalan en /app/share/icons/
    ICON_DIR = "/app/share/icons/hicolor/scalable/apps"
    ICON_THEME_DIR = "/app/share/icons"
    ICON_SRC_DIR = ICON_DIR
else:
    # Usamos el home real ($HOME) en vez de XDG_DATA_HOME porque entornos
    # como Snap sobrescriben XDG_DATA_HOME con un path privado donde el
    # sistema (GNOME Shell, libnotify) no busca iconos.
    _HOME = os.path.expanduser("~")
    ICON_DIR = os.path.join(_HOME, ".local", "share", "icons", "hicolor", "scalable", "apps")
    ICON_THEME_DIR = os.path.join(_HOME, ".local", "share", "icons")
    ICON_SRC_DIR = _PROJECT_ROOT

# Tamaño por defecto de la ventana
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
