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
from unittest.mock import MagicMock, patch


# ── Helpers ─────────────────────────────────────────────────────────

SETTINGS_JSON = "settings.json"
WHATSAPP_URL = "https://web.whatsapp.com/"
WEBKIT_DATA = "webkit-data"
WEBKIT_CACHE = "webkit-cache"


def make_temp_dir():
    """Crea un directorio temporal."""
    return tempfile.mkdtemp()


# ── Test ConfigManager ──────────────────────────────────────────────

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = make_temp_dir()
        from whatsapp_desk.config import ConfigManager, DEFAULT_CONFIG
        self.ConfigManager = ConfigManager
        self.DEFAULT_CONFIG = DEFAULT_CONFIG

    def test_uses_defaults_when_no_file_exists(self):
        cfg = self.ConfigManager(config_dir=self.tmpdir)
        self.assertEqual(cfg.get("dark_mode"), self.DEFAULT_CONFIG["dark_mode"])
        self.assertFalse(cfg.get("dark_mode"))

    def test_get_returns_default_for_missing_key(self):
        cfg = self.ConfigManager(config_dir=self.tmpdir)
        self.assertEqual(cfg.get("nonexistent", "fallback"), "fallback")

    def test_set_persists_value(self):
        cfg = self.ConfigManager(config_dir=self.tmpdir)
        cfg.set("zoom_level", 1.5)
        file_path = os.path.join(self.tmpdir, SETTINGS_JSON)
        self.assertTrue(os.path.isfile(file_path))
        with open(file_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["zoom_level"], 1.5)

    def test_toggle_flips_boolean(self):
        cfg = self.ConfigManager(config_dir=self.tmpdir)
        initial = cfg.get("dark_mode")
        result = cfg.toggle("dark_mode")
        self.assertNotEqual(result, initial)

    def test_loads_existing_config(self):
        file_path = os.path.join(self.tmpdir, SETTINGS_JSON)
        os.makedirs(self.tmpdir, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump({"dark_mode": True, "zoom_level": 1.5}, f)
        cfg = self.ConfigManager(config_dir=self.tmpdir)
        self.assertTrue(cfg.get("dark_mode"))
        self.assertEqual(cfg.get("zoom_level"), 1.5)

    def test_corrupt_json_recovers(self):
        file_path = os.path.join(self.tmpdir, SETTINGS_JSON)
        os.makedirs(self.tmpdir, exist_ok=True)
        with open(file_path, "w") as f:
            f.write("not valid json")
        cfg = self.ConfigManager(config_dir=self.tmpdir)
        self.assertEqual(cfg.get("dark_mode"), self.DEFAULT_CONFIG["dark_mode"])


# ── Test WhatsAppWebView ────────────────────────────────────────────

class TestWhatsAppWebView(unittest.TestCase):
    @staticmethod
    def _make_wv():
        """Crea una instancia de WhatsAppWebView sin ejecutar __init__ real."""
        from whatsapp_desk.webview import WhatsAppWebView
        wv = WhatsAppWebView.__new__(WhatsAppWebView)
        wv.set_property = MagicMock()
        wv.get_user_content_manager = MagicMock()
        wv.set_settings = MagicMock()
        return wv

    @patch("whatsapp_desk.webview.WebKit")
    @patch("whatsapp_desk.webview.GObject")
    def test_settings_created_with_chrome_ua(self, mock_gobject, mock_webkit):
        from whatsapp_desk.resources.ua_chrome import CHROME_USER_AGENT
        mock_settings = MagicMock()
        mock_gobject.new.return_value = mock_settings

        wv = self._make_wv()
        wv._setup_settings()

        # Verificar que GObject.new fue llamado con el UA de Chrome
        mock_gobject.new.assert_called_once()
        call_kwargs = mock_gobject.new.call_args[1]
        self.assertEqual(call_kwargs.get("user_agent"), CHROME_USER_AGENT)

    @patch("whatsapp_desk.webview.WebKit")
    @patch("whatsapp_desk.webview.GObject")
    def test_javascript_enabled(self, mock_gobject, mock_webkit):
        mock_settings = MagicMock()
        mock_gobject.new.return_value = mock_settings

        wv = self._make_wv()
        wv._setup_settings()

        call_kwargs = mock_gobject.new.call_args[1]
        self.assertTrue(call_kwargs.get("enable_javascript"))

    @patch("whatsapp_desk.webview.WebKit")
    @patch("whatsapp_desk.webview.GObject")
    def test_local_storage_enabled(self, mock_gobject, mock_webkit):
        mock_settings = MagicMock()
        mock_gobject.new.return_value = mock_settings

        wv = self._make_wv()
        wv._setup_settings()

        call_kwargs = mock_gobject.new.call_args[1]
        self.assertTrue(call_kwargs.get("enable_html5_local_storage"))

    @patch("whatsapp_desk.webview.WebKit")
    @patch("whatsapp_desk.webview.GObject")
    def test_clipboard_access_enabled(self, mock_gobject, mock_webkit):
        mock_settings = MagicMock()
        mock_gobject.new.return_value = mock_settings

        wv = self._make_wv()
        wv._setup_settings()

        call_kwargs = mock_gobject.new.call_args[1]
        self.assertTrue(call_kwargs.get("javascript_can_access_clipboard"))

    @patch("whatsapp_desk.webview.WebKit")
    @patch("whatsapp_desk.webview.GObject")
    def test_webgl_enabled(self, mock_gobject, mock_webkit):
        mock_settings = MagicMock()
        mock_gobject.new.return_value = mock_settings

        wv = self._make_wv()
        wv._setup_settings()

        call_kwargs = mock_gobject.new.call_args[1]
        self.assertTrue(call_kwargs.get("enable_webgl"))

    @patch("whatsapp_desk.webview.WebKit")
    @patch("whatsapp_desk.webview.GObject")
    def test_settings_applied_to_webview(self, mock_gobject, mock_webkit):
        mock_settings = MagicMock()
        mock_gobject.new.return_value = mock_settings

        wv = self._make_wv()
        wv._setup_settings()

        wv.set_settings.assert_called_once_with(mock_settings)

    @patch("whatsapp_desk.webview.WebKit")
    @patch("whatsapp_desk.webview.GObject")
    def test_load_whatsapp_loads_correct_url(self, mock_gobject, mock_webkit):
        mock_settings = MagicMock()
        mock_gobject.new.return_value = mock_settings

        wv = self._make_wv()
        wv.get_user_content_manager = MagicMock()
        wv._setup_settings()
        wv._inject_browser_spoof = MagicMock()
        wv.load_uri = MagicMock()

        wv.load_whatsapp()
        wv.load_uri.assert_called_once_with(WHATSAPP_URL)


# ── Test WebViewManager ─────────────────────────────────────────────

class TestWebViewManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = make_temp_dir()

    @patch("whatsapp_desk.webview_manager.WebKit")
    @patch("whatsapp_desk.webview_manager.GObject")
    def test_creates_data_directory(self, mock_gobject, mock_webkit):
        from whatsapp_desk.webview_manager import WebViewManager
        WebViewManager(data_home=self.tmpdir)
        self.assertTrue(os.path.isdir(os.path.join(self.tmpdir, WEBKIT_DATA)))
        self.assertTrue(os.path.isdir(os.path.join(self.tmpdir, WEBKIT_CACHE)))

    @patch("whatsapp_desk.webview_manager.WebKit")
    @patch("whatsapp_desk.webview_manager.GObject")
    def test_get_network_session_creates_session(self, mock_gobject, mock_webkit):
        from whatsapp_desk.webview_manager import WebViewManager
        mgr = WebViewManager(data_home=self.tmpdir)
        mgr.get_network_session()
        mock_gobject.new.assert_called_once()

    @patch("whatsapp_desk.webview_manager.WebKit")
    @patch("whatsapp_desk.webview_manager.GObject")
    def test_get_network_session_reuses_session(self, mock_gobject, mock_webkit):
        from whatsapp_desk.webview_manager import WebViewManager
        mgr = WebViewManager(data_home=self.tmpdir)
        s1 = mgr.get_network_session()
        s2 = mgr.get_network_session()
        self.assertIs(s1, s2)
        self.assertEqual(mock_gobject.new.call_count, 1)

    @patch("whatsapp_desk.webview_manager.WebKit")
    @patch("whatsapp_desk.webview_manager.GObject")
    def test_clear_session_resets_state(self, mock_gobject, mock_webkit):
        from whatsapp_desk.webview_manager import WebViewManager
        mgr = WebViewManager(data_home=self.tmpdir)
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
    def test_whatsapp_net_allowed(self, mock_gio):
        from whatsapp_desk.url_handler import UrlHandler
        handler = UrlHandler(MagicMock())
        self.assertTrue(handler._is_whatsapp_url("https://flows.whatsapp.net/cache_management/"))
        self.assertTrue(handler._is_whatsapp_url("https://whatsapp.net/"))
        self.assertTrue(handler._is_whatsapp_url("https://www.whatsapp.net/"))

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


# ── Test StatusNotifierItem ───────────────────────────────────────────

class TestStatusNotifierItem(unittest.TestCase):
    @staticmethod
    def _make_sni(registered=False):
        """Crea una instancia de StatusNotifierItem sin inicializar D-Bus."""
        from whatsapp_desk.status_notifier import StatusNotifierItem
        sni = StatusNotifierItem.__new__(StatusNotifierItem)
        sni._app = MagicMock()
        sni._window = MagicMock()
        sni._connection = None
        sni._registered = registered
        sni._menu_node_id = None
        return sni

    def test_not_available_when_not_registered(self):
        sni = self._make_sni(registered=False)
        self.assertFalse(sni.is_available())

    def test_is_available_when_registered(self):
        sni = self._make_sni(registered=True)
        self.assertTrue(sni.is_available())

    def test_show_window_presents(self):
        sni = self._make_sni(registered=True)
        sni._window.present = MagicMock()
        sni.show_window()
        # GLib.idle_add difiere la ejecución, pero la función se agenda
        sni._window.present.assert_not_called()  # Se ejecuta via idle_add

    def test_toggle_window_hides_visible_window(self):
        sni = self._make_sni(registered=True)
        sni._window.is_visible.return_value = True
        sni._window.hide = MagicMock()
        sni.toggle_window()
        sni._window.hide.assert_called_once()

    def test_toggle_window_shows_hidden_window(self):
        sni = self._make_sni(registered=True)
        sni._window.is_visible.return_value = False
        sni._window.present = MagicMock()
        sni.toggle_window()
        sni._window.present.assert_called_once()


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
    def test_debounce_rapid_messages(self, mock_time, mock_notify, mock_webkit):
        import whatsapp_desk.notifications as nmod
        nmod.NOTIFY_AVAILABLE = True
        mock_wv = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = True

        # Configurar time.time() para devolver valores controlados
        call_count = [0]

        def fake_time():
            call_count[0] += 1
            if call_count[0] <= 2:
                # __init__ asigna _last_notification_time con el valor 0 real,
                # así que time.time solo se llama en _on_message_received
                return 100.0
            return 100.5

        mock_time.time = fake_time

        # Forzar _last_notification_time a 0 (ya está en 0 por defecto)
        mgr = nmod.NotificationManager(mock_wv, mock_cfg)

        mock_js = MagicMock()
        mock_val = MagicMock()
        mock_val.to_string.return_value = '{"count": 1}'
        mock_js.get_js_value.return_value = mock_val

        mgr._on_message_received(None, mock_js)
        self.assertEqual(mock_notify.Notification.new.call_count, 1)

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
        WhatsAppDeskApplication.do_startup(app)
        self.assertIsNotNone(app.config)
        self.assertIsNotNone(app.webview_manager)


# ── Test MainWindow ──────────────────────────────────────────────────

class TestMainWindow(unittest.TestCase):
    def test_hide_to_tray_calls_hide(self):
        """Verifica que hide_to_tray() oculta la ventana."""
        from whatsapp_desk.main_window import MainWindow
        win = MainWindow.__new__(MainWindow)
        win.hide = MagicMock()
        win.hide_to_tray()
        win.hide.assert_called_once()

    def test_close_request_hides_when_tray_available(self):
        """Verifica que close-request oculta la ventana si la bandeja está disponible."""
        from whatsapp_desk.main_window import MainWindow
        win = MainWindow.__new__(MainWindow)
        win._config = MagicMock()
        win._tray = MagicMock()
        win._config.get.return_value = True  # close_to_tray
        win._tray.is_available.return_value = True
        win.hide = MagicMock()
        win.save_geometry = MagicMock()
        result = win._on_close_request(None)
        self.assertTrue(result)
        win.hide.assert_called_once()

    def test_close_request_closes_when_tray_unavailable(self):
        """Verifica que close-request cierra la ventana si la bandeja no está disponible."""
        from whatsapp_desk.main_window import MainWindow
        win = MainWindow.__new__(MainWindow)
        win._config = MagicMock()
        win._tray = MagicMock()
        win._config.get.return_value = True  # close_to_tray
        win._tray.is_available.return_value = False
        win.save_geometry = MagicMock()
        result = win._on_close_request(None)
        self.assertFalse(result)
        win.save_geometry.assert_called_once()


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
