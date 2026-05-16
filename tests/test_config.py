"""Tests para el ConfigManager."""

import json
import os
from whatsapp_desk.config import ConfigManager, DEFAULT_CONFIG


def test_creates_config_dir_on_init(temp_config_dir):
    """Debe crear el directorio de configuración al inicializar."""
    cfg = ConfigManager()
    assert os.path.isdir(temp_config_dir["config"])


def test_uses_defaults_when_no_file_exists(temp_config_dir):
    """Debe usar valores por defecto cuando no existe archivo de config."""
    cfg = ConfigManager()
    assert cfg.get("dark_mode") == DEFAULT_CONFIG["dark_mode"]
    assert cfg.get("notifications_enabled") == DEFAULT_CONFIG["notifications_enabled"]
    assert cfg.get("close_to_tray") == DEFAULT_CONFIG["close_to_tray"]


def test_get_returns_default_for_missing_key(temp_config_dir):
    """get() debe retornar el valor por defecto para claves inexistentes."""
    cfg = ConfigManager()
    assert cfg.get("nonexistent", "fallback") == "fallback"


def test_set_persists_value(temp_config_dir):
    """set() debe persistir el valor en disco."""
    cfg = ConfigManager()
    cfg.set("dark_mode", True)
    # Leer desde disco para verificar persistencia
    file_path = os.path.join(temp_config_dir["config"], "settings.json")
    with open(file_path, "r") as f:
        data = json.load(f)
    assert data["dark_mode"] is True


def test_toggle_flips_boolean(temp_config_dir):
    """toggle() debe alternar valores booleanos."""
    cfg = ConfigManager()
    initial = cfg.get("dark_mode")
    result = cfg.toggle("dark_mode")
    assert result != initial
    assert cfg.get("dark_mode") != initial


def test_loads_existing_config(temp_config_dir):
    """Debe cargar configuración existente desde disco."""
    file_path = os.path.join(temp_config_dir["config"], "settings.json")
    with open(file_path, "w") as f:
        json.dump({"dark_mode": True, "zoom_level": 1.5}, f)
    cfg = ConfigManager()
    assert cfg.get("dark_mode") is True
    assert cfg.get("zoom_level") == 1.5


def test_corrupt_json_recovers_with_defaults(temp_config_dir):
    """Debe recuperarse de un JSON corrupto usando valores por defecto."""
    file_path = os.path.join(temp_config_dir["config"], "settings.json")
    with open(file_path, "w") as f:
        f.write("esto no es json")
    cfg = ConfigManager()
    assert cfg.get("dark_mode") == DEFAULT_CONFIG["dark_mode"]
