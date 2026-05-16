#!/usr/bin/env python3
"""Test runner independiente para WhatsApp Desk.

Ejecuta todos los tests sin necesidad de pytest ni dependencias externas.
Usa únicamente módulos de la biblioteca estándar de Python.
"""

import sys
import os

# Configurar sys.path ANTES que cualquier import de whatsapp_desk
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch, PropertyMock


# ── Helpers ─────────────────────────────────────────────────────────

SETTINGS_JSON = "settings.json"
WHATSAPP_URL = "https://web.whatsapp.com/"


def make_temp_dirs():
    """Crea directorios temporales para config y data."""
    base = tempfile.mkdtemp()
    config_dir = os.path.join(base, "config")
    data_dir = os.path.join(base, "data")
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    return config_dir, data_dir


# ── Test ConfigManager ──────────────────────────────────────────────

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.config_dir, self.data_dir = make_temp_dirs()
        import whatsapp_desk.constants as const
        self._orig_config = const.CONFIG_HOME
        self._orig_data = const.DATA_HOME
        const.CONFIG_HOME = self.config_dir
        const.DATA_HOME = self.data_dir
        from whatsapp_desk.config import ConfigManager, DEFAULT_CONFIG
        self.ConfigManager = ConfigManager
        self.DEFAULT_CONFIG = DEFAULT_CONFIG

    def tearDown(self):
        import whatsapp_desk.constants as const
        const.CONFIG_HOME = self._orig_config
        const.DATA_HOME = self._orig_data

    def test_creates_config_dir_on_init(self):
        self.ConfigManager()
        self.assertTrue(os.path.isdir(self.config_dir))

    def test_uses_defaults_when_no_file_exists(self):
        cfg = self.ConfigManager()
        self.assertEqual(cfg.get("dark_mode"), self.DEFAULT_CONFIG["dark_mode"])
        self.assertEqual(cfg.get("notifications_enabled"), self.DEFAULT_CONFIG["notifications_enabled"])

    def test_get_returns_default_for_missing_key(self):
        cfg = self.ConfigManager()
        self.assertEqual(cfg.get("nonexistent", "fallback"), "fallback")

    def test_set_persists_value(self):
        cfg = self.ConfigManager()
        cfg.set("zoom_level", 1.5)
        file_path = os.path.join(self.config_dir, SETTINGS_JSON)
        with open(file_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["zoom_level"], 1.5)

    def test_toggle_flips_boolean(self):
        cfg = self.ConfigManager()
        initial = cfg.get("dark_mode")
        result = cfg.toggle("dark_mode")
        self.assertNotEqual(result, initial)

    def test_loads_existing_config(self):
        file_path = os.path.join(self.config_dir, SETTINGS_JSON)
        with open(file_path, "w") as f:
            json.dump({"dark_mode": True, "zoom_level": 1.5}, f)
        cfg = self.ConfigManager()
        self.assertTrue(cfg.get("dark_mode"))
        self.assertEqual(cfg.get("zoom_level"), 1.5)

    def test_corrupt_json_recovers(self):
        file_path = os.path.join(self.config_dir, SETTINGS_JSON)
        with open(file_path, "w") as f:
            f.write("not valid json")
        cfg = self.ConfigManager()
        self.assertEqual(cfg.get("dark_mode"), self.DEFAULT_CONFIG["dark_mode"])


# ── Test WhatsAppWebView ────────────────────────────────────────────

class TestWhatsAppWebView(unittest.TestCase):
    def _make_mock_settings(self):
        return MagicMock()

    @patch("whatsapp_desk.webview.WebKit")
    def test_user_agent_set_to_chrome(self, mock_webkit):
        from whatsapp_desk.webview import WhatsAppWebView
        from whatsapp_desk.resources.ua_chrome import CHROME_USER_AGENT

        mock_settings = self._make_mock_settings()
        wv = WhatsAppWebView.__new__(WhatsAppWebView)
        wv.get_settings = MagicMock(return_value=mock_settings)
        wv.set_property = MagicMock()
        wv._setup_settings()

        mock_settings.set_property.assert_any_call("user-agent", CHROME_USER_AGENT)

    @patch("whatsapp_desk.webview.WebKit")
    def test_javascript_enabled(self, mock_webkit):
        from whatsapp_desk.webview import WhatsAppWebView
        mock_settings = self._make_mock_settings()
        wv = WhatsAppWebView.__new__(WhatsAppWebView)
        wv.get_settings = MagicMock(return_value=mock_settings)
        wv.set_property = MagicMock()
        wv._setup_settings()

        mock_settings.set_property.assert_any_call("enable-javascript", True)

    @patch("whatsapp_desk.webview.WebKit")
    def test_local_storage_enabled(self, mock_webkit):
        from whatsapp_desk.webview import WhatsAppWebView
        mock_settings = self._make_mock_settings()
        wv = WhatsAppWebView.__new__(WhatsAppWebView)
        wv.get_settings = MagicMock(return_value=mock_settings)
        wv.set_property = MagicMock()
        wv._setup_settings()

        mock_settings.set_property.assert_any_call("enable-html5-local-storage", True)

    @patch("whatsapp_desk.webview.WebKit")
    def test_clipboard_access_enabled(self, mock_webkit):
        from whatsapp_desk.webview import WhatsAppWebView
        mock_settings = self._make_mock_settings()
        wv = WhatsAppWebView.__new__(WhatsAppWebView)
        wv.get_settings = MagicMock(return_value=mock_settings)
        wv.set_property = MagicMock()
        wv._setup_settings()

        mock_settings.set_property.assert_any_call("javascript-can-access-clipboard", True)

    @patch("whatsapp_desk.webview.WebKit")
    def test_webgl_enabled(self, mock_webkit):
        from whatsapp_desk.webview import WhatsAppWebView
        mock_settings = self._make_mock_settings()
        wv = WhatsAppWebView.__new__(WhatsAppWebView)
        wv.get_settings = MagicMock(return_value=mock_settings)
        wv.set_property = MagicMock()
        wv._setup_settings()

        mock_settings.set_property.assert_any_call("enable-webgl", True)

    @patch("whatsapp_desk.webview.WebKit")
    def test_network_session_set_on_webview(self, mock_webkit):
        from whatsapp_desk.webview import WhatsAppWebView
        mock_settings = self._make_mock_settings()
        mock_ns = MagicMock()

        wv = WhatsAppWebView.__new__(WhatsAppWebView)
        wv.get_settings = MagicMock(return_value=mock_settings)
        wv.set_property = MagicMock()
        wv._setup_settings()

        # Simular lo que hace __init__ con network_session
        wv.set_property("network-session", mock_ns)
        wv.set_property.assert_called_with("network-session", mock_ns)

    @patch("whatsapp_desk.webview.WebKit")
    def test_load_whatsapp_loads_correct_url(self, mock_webkit):
        from whatsapp_desk.webview import WhatsAppWebView
        mock_settings = self._make_mock_settings()
        wv = WhatsAppWebView.__new__(WhatsAppWebView)
        wv.get_settings = MagicMock(return_value=mock_settings)
        wv.set_property = MagicMock()
        wv.load_uri = MagicMock()
        wv._setup_settings()

        wv.load_whatsapp()
        wv.load_uri.assert_called_once_with(WHATSAPP_URL)


# ── Test WebViewManager ─────────────────────────────────────────────

class TestWebViewManager(unittest.TestCase):
    def setUp(self):
        self.config_dir, self.data_dir = make_temp_dirs()
        import whatsapp_desk.constants as const
        self._orig_data = const.DATA_HOME
        const.DATA_HOME = self.data_dir

    def tearDown(self):
        import whatsapp_desk.constants as const
        const.DATA_HOME = self._orig_data

    @patch("whatsapp_desk.webview_manager.WebKit")
    @patch("whatsapp_desk.webview_manager.GObject")
    def test_creates_data_directory(self, mock_gobject, mock_webkit):
        from whatsapp_desk.webview_manager import WebViewManager
        mgr = WebViewManager()
        self.assertTrue(os.path.isdir(os.path.join(self.data_dir, "webkit-data")))
        self.assertTrue(os.path.isdir(os.path.join(self.data_dir, "webkit-cache")))

    @patch("whatsapp_desk.webview_manager.WebKit")
    @patch("whatsapp_desk.webview_manager.GObject")
    def test_get_network_session_creates_session(self, mock_gobject, mock_webkit):
        from whatsapp_desk.webview_manager import WebViewManager
        mgr = WebViewManager()
        mgr.get_network_session()
        mock_gobject.new.assert_called_once()

    @patch("whatsapp_desk.webview_manager.WebKit")
    @patch("whatsapp_desk.webview_manager.GObject")
    def test_get_network_session_reuses_session(self, mock_gobject, mock_webkit):
        from whatsapp_desk.webview_manager import WebViewManager
        mgr = WebViewManager()
        s1 = mgr.get_network_session()
        s2 = mgr.get_network_session()
        self.assertIs(s1, s2)
        self.assertEqual(mock_gobject.new.call_count, 1)

    @patch("whatsapp_desk.webview_manager.WebKit")
    @patch("whatsapp_desk.webview_manager.GObject")
    def test_clear_session_resets_state(self, mock_gobject, mock_webkit):
        from whatsapp_desk.webview_manager import WebViewManager
        mgr = WebViewManager()
        mgr.get_network_session()
        mgr.clear_session()
        self.assertIsNone(mgr._network_session)


# ── Test UrlHandler ─────────────────────────────────────────────────

class TestUrlHandler(unittest.TestCase):
    @patch("whatsapp_desk.url_handler.Gio")
    def test_whatsapp_url_allowed(self, mock_gio):
        from whatsapp_desk.url_handler import UrlHandler
        handler = UrlHandler(MagicMock())
        self.assertTrue(handler._is_whatsapp_url(WHATSAPP_URL))
        self.assertTrue(handler._is_whatsapp_url("https://whatsapp.com/"))

    @patch("whatsapp_desk.url_handler.Gio")
    def test_external_url_blocked(self, mock_gio):
        from whatsapp_desk.url_handler import UrlHandler
        handler = UrlHandler(MagicMock())
        self.assertFalse(handler._is_whatsapp_url("https://google.com"))

    @patch("whatsapp_desk.url_handler.Gio")
    def test_open_external_launches_browser(self, mock_gio):
        from whatsapp_desk.url_handler import UrlHandler
        handler = UrlHandler(MagicMock())
        handler._open_external("https://example.com")
        mock_gio.AppInfo.launch_default_for_uri.assert_called_once_with("https://example.com")

    @patch("whatsapp_desk.url_handler.Gio")
    def test_decide_policy_allows_whatsapp(self, mock_gio):
        from whatsapp_desk.url_handler import UrlHandler
        handler = UrlHandler(MagicMock())

        mock_decision = MagicMock()
        mock_nav = MagicMock()
        mock_req = MagicMock()
        mock_req.get_uri.return_value = WHATSAPP_URL
        mock_nav.get_request.return_value = mock_req
        mock_decision.get_navigation_action.return_value = mock_nav

        result = handler._on_decide_policy(None, mock_decision, "NAVIGATION_ACTION")
        self.assertFalse(result)


# ── Test TrayIcon ───────────────────────────────────────────────────

class TestTrayIcon(unittest.TestCase):
    @patch("whatsapp_desk.tray.Gio")
    @patch("whatsapp_desk.tray.AppIndicator")
    def test_creates_indicator_when_available(self, mock_ai, mock_gio):
        import whatsapp_desk.tray as tray_mod
        tray_mod.TRAY_AVAILABLE = True
        tray = tray_mod.TrayIcon(MagicMock(), MagicMock())
        self.assertTrue(tray.is_available())

    @patch("whatsapp_desk.tray.Gio")
    @patch("whatsapp_desk.tray.AppIndicator")
    def test_handles_failure_gracefully(self, mock_ai, mock_gio):
        import whatsapp_desk.tray as tray_mod
        tray_mod.TRAY_AVAILABLE = True
        mock_ai.Indicator.new.side_effect = RuntimeError("fail")
        tray = tray_mod.TrayIcon(MagicMock(), MagicMock())
        self.assertFalse(tray.is_available())

    def test_not_available_when_library_missing(self):
        import whatsapp_desk.tray as tray_mod
        tray_mod.TRAY_AVAILABLE = False
        tray = tray_mod.TrayIcon(MagicMock(), MagicMock())
        self.assertFalse(tray.is_available())

    @patch("whatsapp_desk.tray.Gio")
    @patch("whatsapp_desk.tray.AppIndicator")
    def test_show_window_presents(self, mock_ai, mock_gio):
        import whatsapp_desk.tray as tray_mod
        tray_mod.TRAY_AVAILABLE = True
        mock_win = MagicMock()
        tray = tray_mod.TrayIcon(MagicMock(), mock_win)
        tray.show_window()
        mock_win.present.assert_called_once()


# ── Test NotificationManager ────────────────────────────────────────

class TestNotificationManager(unittest.TestCase):
    @patch("whatsapp_desk.notifications.WebKit")
    @patch("whatsapp_desk.notifications.Notify")
    def test_registers_script_handler(self, mock_notify, mock_webkit):
        import whatsapp_desk.notifications as nmod
        nmod.NOTIFY_AVAILABLE = True
        mock_wv = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = True

        nmod.NotificationManager(mock_wv, mock_cfg)
        uc = mock_wv.get_user_content_manager.return_value
        uc.register_script_message_handler.assert_called_once_with(
            nmod.NotificationManager.HANDLER_NAME
        )

    @patch("whatsapp_desk.notifications.WebKit")
    @patch("whatsapp_desk.notifications.Notify")
    def test_injects_javascript(self, mock_notify, mock_webkit):
        import whatsapp_desk.notifications as nmod
        nmod.NOTIFY_AVAILABLE = True
        mock_wv = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = True

        nmod.NotificationManager(mock_wv, mock_cfg)
        mock_wv.inject_javascript.assert_called_once()

    @patch("whatsapp_desk.notifications.WebKit")
    @patch("whatsapp_desk.notifications.Notify")
    def test_no_notification_when_disabled(self, mock_notify, mock_webkit):
        import whatsapp_desk.notifications as nmod
        nmod.NOTIFY_AVAILABLE = True
        mock_wv = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.get.side_effect = lambda k, d=None: (
            False if k == "notifications_enabled" else d
        )

        mgr = nmod.NotificationManager(mock_wv, mock_cfg)
        mock_js = MagicMock()
        mock_val = MagicMock()
        mock_val.to_string.return_value = '{"count": 1}'
        mock_js.get_js_value.return_value = mock_val

        mgr._on_message_received(None, mock_js)
        mock_notify.Notification.new.assert_not_called()

    @patch("whatsapp_desk.notifications.WebKit")
    @patch("whatsapp_desk.notifications.Notify")
    @patch("whatsapp_desk.notifications.time")
    def test_debounce_rapid_messages(self, mock_notify, mock_webkit, mock_time):
        import whatsapp_desk.notifications as nmod
        nmod.NOTIFY_AVAILABLE = True
        mock_wv = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = True

        mock_time.time.return_value = 100.0
        mgr = nmod.NotificationManager(mock_wv, mock_cfg)

        mock_js = MagicMock()
        mock_val = MagicMock()
        mock_val.to_string.return_value = '{"count": 1}'
        mock_js.get_js_value.return_value = mock_val

        mgr._on_message_received(None, mock_js)
        self.assertEqual(mock_notify.Notification.new.call_count, 1)

        mock_time.time.return_value = 100.5
        mgr._on_message_received(None, mock_js)
        self.assertEqual(mock_notify.Notification.new.call_count, 1)


# ── Test DarkModeManager ────────────────────────────────────────────

class TestDarkModeManager(unittest.TestCase):
    @patch("whatsapp_desk.dark_mode.Gtk")
    def test_apply_sets_gtk_setting(self, mock_gtk):
        from whatsapp_desk.dark_mode import DarkModeManager
        mock_gs = MagicMock()
        mock_gtk.Settings.get_default.return_value = mock_gs
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = True

        DarkModeManager(MagicMock(), mock_cfg)
        mock_gs.set_property.assert_called_with(
            "gtk-application-prefer-dark-theme", True
        )

    @patch("whatsapp_desk.dark_mode.Gtk")
    def test_toggle_returns_new_value(self, mock_gtk):
        from whatsapp_desk.dark_mode import DarkModeManager
        mock_gs = MagicMock()
        mock_gtk.Settings.get_default.return_value = mock_gs
        mock_cfg = MagicMock()
        mock_cfg.toggle.return_value = True

        dm = DarkModeManager(MagicMock(), mock_cfg)
        result = dm.toggle()
        self.assertTrue(result)
        mock_cfg.toggle.assert_called_once_with("dark_mode")

    @patch("whatsapp_desk.dark_mode.Gtk")
    def test_apply_reads_config(self, mock_gtk):
        from whatsapp_desk.dark_mode import DarkModeManager
        mock_gs = MagicMock()
        mock_gtk.Settings.get_default.return_value = mock_gs
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = False

        DarkModeManager(MagicMock(), mock_cfg)
        mock_gs.set_property.assert_called_with(
            "gtk-application-prefer-dark-theme", False
        )


# ── Test Application ────────────────────────────────────────────────

class TestApplication(unittest.TestCase):
    @patch("whatsapp_desk.application.signal")
    @patch("whatsapp_desk.application.GLib")
    @patch("whatsapp_desk.application.Gio")
    @patch("whatsapp_desk.application.Gtk")
    def test_config_initialized_on_startup(self, mock_gtk, mock_gio, mock_glib, mock_sig):
        from whatsapp_desk.application import WhatsAppDeskApplication
        app = WhatsAppDeskApplication.__new__(WhatsAppDeskApplication)
        app.add_main_option = MagicMock()
        app.add_action = MagicMock()
        app._config = None
        app._webview_manager = None
        app._window = None

        # Simular do_startup sin GTK
        WhatsAppDeskApplication.do_startup(app)
        self.assertIsNotNone(app.config)
        self.assertIsNotNone(app.webview_manager)


# ── Test constants ──────────────────────────────────────────────────

class TestConstants(unittest.TestCase):
    def test_app_id(self):
        from whatsapp_desk.constants import APP_ID
        self.assertEqual(APP_ID, "com.vladzur.WhatsAppDesk")

    def test_whatsapp_url(self):
        from whatsapp_desk.constants import WHATSAPP_URL
        self.assertEqual(WHATSAPP_URL, "https://web.whatsapp.com/")


# ── Main ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
