"""Constantes globales de la aplicación."""

# Identificador único D-Bus para single-instance
APP_ID = "com.vladzur.WhatsAppDesk"

# URL de WhatsApp Web
WHATSAPP_URL = "https://web.whatsapp.com/"

# Directorios de datos de la aplicación
import os
DATA_HOME = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "whatsapp-desk",
)
CONFIG_HOME = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "whatsapp-desk",
)

# Tamaño por defecto de la ventana
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
