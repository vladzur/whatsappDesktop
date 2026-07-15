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


# ── Helpers para tests de bandeja y notificaciones ───────────────────

def _make_fake_notification(title="Nuevo mensaje", body="Juan: Hola"):
    """Crea un mock de WebKit.Notification con título y cuerpo."""
    notif = MagicMock()
    notif.get_title.return_value = title
    notif.get_body.return_value = body
    return notif


# ── Test StatusNotifierItem ───────────────────────────────────────────

class TestStatusNotifierItem(unittest.TestCase):
    @staticmethod
    def _make_sni(registered=False, current_icon=None):
        """Crea una instancia de StatusNotifierItem sin inicializar D-Bus."""
        from whatsapp_desk.status_notifier import (
            StatusNotifierItem, _ICON_NORMAL, _ICON_UNREAD,
        )
        sni = StatusNotifierItem.__new__(StatusNotifierItem)
        sni._app = MagicMock()
        sni._window = MagicMock()
        sni._connection = None
        sni._registered = registered
        sni._current_icon = current_icon or _ICON_NORMAL
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

    # ── Badge de mensajes no leídos ──────────────────────────────────

    def test_set_unread_changes_icon(self):
        """set_unread con count > 0 debe cambiar al icono de badge."""
        from whatsapp_desk.status_notifier import _ICON_UNREAD

        sni = self._make_sni()
        sni._emit_new_icon = MagicMock()
        sni.set_unread(3)
        self.assertEqual(sni._current_icon, _ICON_UNREAD)

    def test_set_unread_zero_delegates_to_clear(self):
        """set_unread(0) debe delegar en clear_unread()."""
        sni = self._make_sni(current_icon=None)  # se asigna _ICON_UNREAD
        from whatsapp_desk.status_notifier import _ICON_UNREAD
        sni._current_icon = _ICON_UNREAD
        sni.clear_unread = MagicMock()
        sni.set_unread(0)
        sni.clear_unread.assert_called_once()

    def test_clear_unread_restores_icon(self):
        """clear_unread debe volver al icono normal."""
        from whatsapp_desk.status_notifier import _ICON_NORMAL, _ICON_UNREAD

        sni = self._make_sni(current_icon=_ICON_UNREAD)
        sni._emit_new_icon = MagicMock()
        sni.clear_unread()
        self.assertEqual(sni._current_icon, _ICON_NORMAL)

    def test_set_unread_when_already_unread_is_noop(self):
        """No debe emitir señal redundante si el icono ya es unread."""
        from whatsapp_desk.status_notifier import _ICON_UNREAD

        sni = self._make_sni(current_icon=_ICON_UNREAD)
        sni._emit_new_icon = MagicMock()
        sni.set_unread(5)
        sni._emit_new_icon.assert_not_called()

    def test_clear_unread_when_already_clean_is_noop(self):
        """No debe emitir señal redundante si el icono ya está limpio."""
        sni = self._make_sni()
        sni._emit_new_icon = MagicMock()
        sni.clear_unread()
        sni._emit_new_icon.assert_not_called()

    def test_emit_new_icon_sends_dbus_signal(self):
        """_emit_new_icon debe emitir la señal NewIcon del protocolo SNI."""
        sni = self._make_sni(registered=True)
        sni._connection = MagicMock()
        sni._emit_new_icon()
        sni._connection.emit_signal.assert_called_once()

    def test_emit_new_icon_skips_when_not_registered(self):
        """No debe emitir D-Bus si no está registrado en el Watcher."""
        sni = self._make_sni(registered=False)
        sni._connection = MagicMock()
        sni._emit_new_icon()
        sni._connection.emit_signal.assert_not_called()


# ── Test NotificationManager ────────────────────────────────────────

class TestNotificationManager(unittest.TestCase):
    @staticmethod
    def _make_mgr(notifications_enabled=True, on_new_message=None):
        """Crea un NotificationManager con dependencias mockeadas."""
        import whatsapp_desk.notifications as nmod
        nmod.NOTIFY_AVAILABLE = True
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = notifications_enabled
        mgr = nmod.NotificationManager(mock_cfg, on_new_message=on_new_message)
        return mgr, mock_cfg, nmod

    @patch("whatsapp_desk.notifications.Notify")
    def test_init_calls_notify_init(self, mock_notify):
        """Debe inicializar libnotify cuando está disponible."""
        import whatsapp_desk.notifications as nmod
        nmod.NOTIFY_AVAILABLE = True
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = True
        nmod.NotificationManager(mock_cfg)
        mock_notify.init.assert_called_once_with("com.vladzur.WhatsAppDesk")

    @patch("whatsapp_desk.notifications.Notify")
    def test_init_starts_with_zero_count(self, mock_notify):
        """Debe inicializar el contador de no leídos en 0."""
        mgr, _, _ = self._make_mgr()
        self.assertEqual(mgr._unread_count, 0)

    @patch("whatsapp_desk.notifications.Notify")
    def test_handle_notification_shows_libnotify(self, mock_notify):
        """Debe mostrar una burbuja de escritorio vía libnotify."""
        mgr, _, _ = self._make_mgr()
        notif = _make_fake_notification(title="Título", body="Cuerpo")
        result = mgr.handle_webkit_notification(notif)
        self.assertTrue(result)
        mock_notify.Notification.new.assert_called_once()
        mock_notify.Notification.new.return_value.show.assert_called_once()

    @patch("whatsapp_desk.notifications.Notify")
    def test_handle_notification_returns_true_when_disabled(self, mock_notify):
        """Debe retornar True aunque las notificaciones estén desactivadas."""
        mgr, _, _ = self._make_mgr(notifications_enabled=False)
        notif = _make_fake_notification()
        result = mgr.handle_webkit_notification(notif)
        self.assertTrue(result)
        mock_notify.Notification.new.assert_not_called()

    @patch("whatsapp_desk.notifications.Notify")
    def test_handle_notification_increments_count(self, mock_notify):
        """Debe incrementar el contador de mensajes no leídos."""
        mgr, _, _ = self._make_mgr()
        mgr.handle_webkit_notification(_make_fake_notification())
        self.assertEqual(mgr._unread_count, 1)
        mgr.handle_webkit_notification(_make_fake_notification())
        self.assertEqual(mgr._unread_count, 2)

    @patch("whatsapp_desk.notifications.Notify")
    def test_handle_notification_calls_callback(self, mock_notify):
        """Debe invocar on_new_message con el conteo actualizado."""
        cb = MagicMock()
        mgr, _, _ = self._make_mgr(on_new_message=cb)
        mgr.handle_webkit_notification(_make_fake_notification())
        cb.assert_called_with(1)
        mgr.handle_webkit_notification(_make_fake_notification())
        cb.assert_called_with(2)

    @patch("whatsapp_desk.notifications.Notify")
    def test_debounce_prevents_duplicate_popups(self, mock_notify):
        """No debe mostrar burbuja duplicada en rápida sucesión."""
        mgr, _, _ = self._make_mgr()
        mgr.handle_webkit_notification(_make_fake_notification())
        self.assertEqual(mock_notify.Notification.new.call_count, 1)
        mgr.handle_webkit_notification(_make_fake_notification())
        self.assertEqual(mock_notify.Notification.new.call_count, 1)

    @patch("whatsapp_desk.notifications.Notify")
    def test_debounce_still_counts(self, mock_notify):
        """Aunque se omita la burbuja por debounce, el conteo debe subir."""
        mgr, _, _ = self._make_mgr()
        mgr.handle_webkit_notification(_make_fake_notification())
        mgr.handle_webkit_notification(_make_fake_notification())
        self.assertEqual(mgr._unread_count, 2)

    @patch("whatsapp_desk.notifications.Notify")
    def test_reset_unread_zeroes_count(self, mock_notify):
        """reset_unread() debe reiniciar el contador a 0."""
        mgr, _, _ = self._make_mgr()
        mgr.handle_webkit_notification(_make_fake_notification())
        mgr.handle_webkit_notification(_make_fake_notification())
        mgr.reset_unread()
        self.assertEqual(mgr._unread_count, 0)

    @patch("whatsapp_desk.notifications.Notify")
    def test_reset_unread_calls_callback_with_zero(self, mock_notify):
        """reset_unread() debe invocar on_new_message con 0."""
        cb = MagicMock()
        mgr, _, _ = self._make_mgr(on_new_message=cb)
        mgr.handle_webkit_notification(_make_fake_notification())
        mgr.reset_unread()
        cb.assert_called_with(0)

    @patch("whatsapp_desk.notifications.Notify")
    def test_reset_unread_without_callback_does_not_crash(self, mock_notify):
        """reset_unread() no debe fallar si no hay callback registrado."""
        mgr, _, _ = self._make_mgr(on_new_message=None)
        mgr.handle_webkit_notification(_make_fake_notification())
        mgr.reset_unread()
        self.assertEqual(mgr._unread_count, 0)

    @patch("whatsapp_desk.notifications.Notify")
    def test_handle_notification_falls_back_to_defaults(self, mock_notify):
        """Debe usar valores por defecto si título o cuerpo están vacíos."""
        mgr, _, _ = self._make_mgr()
        notif = _make_fake_notification(title="", body="")
        mgr.handle_webkit_notification(notif)
        mock_notify.Notification.new.assert_called_once_with(
            "WhatsApp Desk", "Tienes un nuevo mensaje", "whatsapp-desk-symbolic"
        )

    @patch("whatsapp_desk.notifications.Notify")
    def test_notify_unavailable_does_not_crash(self, mock_notify):
        """No debe fallar cuando libnotify no está instalado."""
        import whatsapp_desk.notifications as nmod
        nmod.NOTIFY_AVAILABLE = False
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = True
        mgr = nmod.NotificationManager(mock_cfg)
        notif = _make_fake_notification()
        result = mgr.handle_webkit_notification(notif)
        self.assertTrue(result)
        self.assertEqual(mgr._unread_count, 1)


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
        win.force_quit = False
        win.hide = MagicMock()
        win.hide_to_tray()
        win.hide.assert_called_once()

    def test_close_request_hides_when_tray_available(self):
        """Verifica que close-request oculta la ventana si la bandeja está disponible."""
        from whatsapp_desk.main_window import MainWindow
        win = MainWindow.__new__(MainWindow)
        win.force_quit = False
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
        win.force_quit = False
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


# ── Test UrlHandler RESPONSE decisions ──────────────────────────────

class TestUrlHandlerResponse(unittest.TestCase):
    """Tests para decisiones de política RESPONSE (descargas)."""

    @patch("whatsapp_desk.url_handler.Gio")
    def test_unsupported_mime_triggers_download(self, mock_gio):
        """MIME types no soportados por WebKit deben descargarse."""
        from whatsapp_desk.url_handler import UrlHandler
        from gi.repository import WebKit

        handler = UrlHandler(MagicMock())
        mock_decision = MagicMock()
        mock_decision.is_mime_type_supported.return_value = False

        result = handler._on_decide_policy(
            None, mock_decision, WebKit.PolicyDecisionType.RESPONSE
        )
        self.assertTrue(result)
        mock_decision.download.assert_called_once()

    @patch("whatsapp_desk.url_handler.Gio")
    def test_binary_mime_triggers_download(self, mock_gio):
        """MIME types binarios (application/pdf) deben descargarse aunque WebKit los soporte."""
        from whatsapp_desk.url_handler import UrlHandler
        from gi.repository import WebKit

        handler = UrlHandler(MagicMock())
        mock_decision = MagicMock()
        mock_decision.is_mime_type_supported.return_value = True
        mock_response = MagicMock()
        mock_response.get_mime_type.return_value = "application/pdf"
        mock_decision.get_response.return_value = mock_response

        result = handler._on_decide_policy(
            None, mock_decision, WebKit.PolicyDecisionType.RESPONSE
        )
        self.assertTrue(result)
        mock_decision.download.assert_called_once()

    @patch("whatsapp_desk.url_handler.Gio")
    def test_zip_mime_triggers_download(self, mock_gio):
        """MIME types comprimidos deben descargarse."""
        from whatsapp_desk.url_handler import UrlHandler
        from gi.repository import WebKit

        handler = UrlHandler(MagicMock())
        mock_decision = MagicMock()
        mock_decision.is_mime_type_supported.return_value = True
        mock_response = MagicMock()
        mock_response.get_mime_type.return_value = "application/zip"
        mock_decision.get_response.return_value = mock_response

        result = handler._on_decide_policy(
            None, mock_decision, WebKit.PolicyDecisionType.RESPONSE
        )
        self.assertTrue(result)
        mock_decision.download.assert_called_once()

    @patch("whatsapp_desk.url_handler.Gio")
    def test_html_mime_allowed_in_webview(self, mock_gio):
        """MIME types navegables (text/html) deben mostrarse en el WebView."""
        from whatsapp_desk.url_handler import UrlHandler
        from gi.repository import WebKit

        handler = UrlHandler(MagicMock())
        mock_decision = MagicMock()
        mock_decision.is_mime_type_supported.return_value = True
        mock_response = MagicMock()
        mock_response.get_mime_type.return_value = "text/html"
        mock_decision.get_response.return_value = mock_response

        result = handler._on_decide_policy(
            None, mock_decision, WebKit.PolicyDecisionType.RESPONSE
        )
        self.assertFalse(result)
        mock_decision.download.assert_not_called()

    @patch("whatsapp_desk.url_handler.Gio")
    def test_audio_mime_allowed_in_webview(self, mock_gio):
        """MIME types de audio deben reproducirse en el WebView."""
        from whatsapp_desk.url_handler import UrlHandler
        from gi.repository import WebKit

        handler = UrlHandler(MagicMock())
        mock_decision = MagicMock()
        mock_decision.is_mime_type_supported.return_value = True
        mock_response = MagicMock()
        mock_response.get_mime_type.return_value = "audio/mpeg"
        mock_decision.get_response.return_value = mock_response

        result = handler._on_decide_policy(
            None, mock_decision, WebKit.PolicyDecisionType.RESPONSE
        )
        self.assertFalse(result)
        mock_decision.download.assert_not_called()

    @patch("whatsapp_desk.url_handler.Gio")
    def test_video_mime_allowed_in_webview(self, mock_gio):
        """MIME types de video deben reproducirse en el WebView."""
        from whatsapp_desk.url_handler import UrlHandler
        from gi.repository import WebKit

        handler = UrlHandler(MagicMock())
        mock_decision = MagicMock()
        mock_decision.is_mime_type_supported.return_value = True
        mock_response = MagicMock()
        mock_response.get_mime_type.return_value = "video/mp4"
        mock_decision.get_response.return_value = mock_response

        result = handler._on_decide_policy(
            None, mock_decision, WebKit.PolicyDecisionType.RESPONSE
        )
        self.assertFalse(result)
        mock_decision.download.assert_not_called()

    @patch("whatsapp_desk.url_handler.Gio")
    def test_svg_image_allowed_in_webview(self, mock_gio):
        """MIME types SVG deben renderizarse en el WebView."""
        from whatsapp_desk.url_handler import UrlHandler
        from gi.repository import WebKit

        handler = UrlHandler(MagicMock())
        mock_decision = MagicMock()
        mock_decision.is_mime_type_supported.return_value = True
        mock_response = MagicMock()
        mock_response.get_mime_type.return_value = "image/svg+xml"
        mock_decision.get_response.return_value = mock_response

        result = handler._on_decide_policy(
            None, mock_decision, WebKit.PolicyDecisionType.RESPONSE
        )
        self.assertFalse(result)
        mock_decision.download.assert_not_called()

    @patch("whatsapp_desk.url_handler.Gio")
    def test_none_mime_triggers_download(self, mock_gio):
        """Si get_mime_type retorna None, se fuerza descarga como binario."""
        from whatsapp_desk.url_handler import UrlHandler
        from gi.repository import WebKit

        handler = UrlHandler(MagicMock())
        mock_decision = MagicMock()
        mock_decision.is_mime_type_supported.return_value = True
        mock_response = MagicMock()
        mock_response.get_mime_type.return_value = None
        mock_decision.get_response.return_value = mock_response

        result = handler._on_decide_policy(
            None, mock_decision, WebKit.PolicyDecisionType.RESPONSE
        )
        self.assertTrue(result)
        mock_decision.download.assert_called_once()


# ── Test WhatsAppWebView permissions ────────────────────────────────

class TestWhatsAppWebViewPermissions(unittest.TestCase):
    """Tests para manejo de permisos del WebView (micrófono, cámara, notificaciones)."""

    @staticmethod
    def _make_wv():
        """Crea una instancia de WhatsAppWebView sin ejecutar __init__ real."""
        from whatsapp_desk.webview import WhatsAppWebView

        wv = WhatsAppWebView.__new__(WhatsAppWebView)
        wv.set_property = MagicMock()
        wv.get_user_content_manager = MagicMock()
        wv.set_settings = MagicMock()
        wv.get_root = MagicMock()
        return wv

    @patch("whatsapp_desk.webview.Gtk")
    @patch("whatsapp_desk.webview.GObject")
    def test_notification_permission_auto_allowed(self, mock_gobj, mock_gtk):
        """Permisos de notificación se conceden automáticamente."""
        from gi.repository import WebKit

        wv = self._make_wv()
        # Usar spec con la clase real para que isinstance funcione
        mock_request = MagicMock(spec=WebKit.NotificationPermissionRequest)

        result = wv._on_permission_request(wv, mock_request)
        self.assertTrue(result)
        mock_request.allow.assert_called_once()

    @patch("whatsapp_desk.webview.Gtk")
    @patch("whatsapp_desk.webview.GObject")
    def test_user_media_permission_shows_dialog(self, mock_gobj, mock_gtk):
        """Permisos de micrófono/cámara muestran diálogo de confirmación."""
        from gi.repository import WebKit

        wv = self._make_wv()
        mock_request = MagicMock(spec=WebKit.UserMediaPermissionRequest)

        result = wv._on_permission_request(wv, mock_request)
        self.assertTrue(result)
        mock_dialog = mock_gtk.AlertDialog.return_value
        mock_dialog.choose.assert_called_once()

    @patch("whatsapp_desk.webview.Gtk")
    @patch("whatsapp_desk.webview.GObject")
    def test_device_info_permission_shows_dialog(self, mock_gobj, mock_gtk):
        """Permisos de DeviceInfo también muestran diálogo de confirmación."""
        from gi.repository import WebKit

        wv = self._make_wv()
        mock_request = MagicMock(spec=WebKit.DeviceInfoPermissionRequest)

        result = wv._on_permission_request(wv, mock_request)
        self.assertTrue(result)
        mock_dialog = mock_gtk.AlertDialog.return_value
        mock_dialog.choose.assert_called_once()

    @patch("whatsapp_desk.webview.Gtk")
    @patch("whatsapp_desk.webview.GObject")
    def test_unknown_permission_denied(self, mock_gobj, mock_gtk):
        """Permisos no reconocidos se deniegan por defecto."""
        wv = self._make_wv()
        mock_request = MagicMock()

        result = wv._on_permission_request(wv, mock_request)
        self.assertTrue(result)
        mock_request.deny.assert_called_once()


# ── Test DownloadManager ────────────────────────────────────────────

class TestDownloadManager(unittest.TestCase):
    """Tests para el gestor de descargas."""

    @patch("whatsapp_desk.download_manager.GLib")
    def test_init_connects_download_started_signal(self, mock_glib):
        """Al inicializar, conecta la señal download-started de NetworkSession."""
        from whatsapp_desk.download_manager import DownloadManager

        mock_session = MagicMock()
        mock_window = MagicMock()
        DownloadManager(mock_session, mock_window)
        mock_session.connect.assert_called_once_with(
            "download-started", mock_session.connect.call_args[0][1]
        )

    @patch("whatsapp_desk.download_manager.GLib")
    def test_on_download_started_connects_signals(self, mock_glib):
        """Al iniciar descarga, conecta señales decide-destination, finished, failed y progress."""
        from whatsapp_desk.download_manager import DownloadManager

        mock_session = MagicMock()
        mock_window = MagicMock()
        dm = DownloadManager(mock_session, mock_window)

        mock_download = MagicMock()
        dm._on_download_started(mock_session, mock_download)

        # Verificar que conectó las 4 señales esperadas
        connected_signals = {call[0][0] for call in mock_download.connect.call_args_list}
        expected = {
            "decide-destination",
            "finished",
            "failed",
            "notify::estimated-progress",
        }
        self.assertEqual(connected_signals, expected)

    @patch("whatsapp_desk.download_manager.GLib")
    def test_failed_with_cancel_code_shows_no_alert(self, mock_glib):
        """Descarga cancelada por el usuario (código 400) no muestra alerta."""
        from whatsapp_desk.download_manager import DownloadManager

        mock_session = MagicMock()
        mock_window = MagicMock()
        dm = DownloadManager(mock_session, mock_window)
        dm._restore_title = MagicMock()

        mock_download = MagicMock()
        mock_error = MagicMock()
        mock_error.code = 400  # Código de cancelación del usuario

        dm._on_download_failed(mock_download, mock_error)
        dm._restore_title.assert_called_once()
        # El download debe ser removido del diccionario activo
        self.assertNotIn(mock_download, dm._active_downloads)

    @patch("whatsapp_desk.download_manager.GLib")
    def test_failed_with_other_error_shows_alert(self, mock_glib):
        """Error distinto de cancelación muestra AlertDialog."""
        from whatsapp_desk.download_manager import DownloadManager

        mock_session = MagicMock()
        mock_window = MagicMock()
        dm = DownloadManager(mock_session, mock_window)
        dm._restore_title = MagicMock()

        mock_download = MagicMock()
        mock_error = MagicMock()
        mock_error.code = 1  # Error real (ej: network error)

        # El AlertDialog se crea con Gtk.AlertDialog(), que viene del módulo
        with patch("whatsapp_desk.download_manager.Gtk") as mock_gtk:
            dm._on_download_failed(mock_download, mock_error)

        mock_alert = mock_gtk.AlertDialog.return_value
        mock_alert.set_message.assert_called_once_with("Error al descargar")
        mock_alert.show.assert_called_once_with(mock_window)
        dm._restore_title.assert_called_once()

    @patch("whatsapp_desk.download_manager.GLib")
    def test_finished_restores_title_and_notifies(self, mock_glib):
        """Al finalizar descarga, restaura título y muestra notificación de éxito."""
        from whatsapp_desk.download_manager import DownloadManager

        mock_session = MagicMock()
        mock_window = MagicMock()
        dm = DownloadManager(mock_session, mock_window)

        mock_download = MagicMock()
        dm._active_downloads[mock_download] = "/tmp/archivo.pdf"

        with patch("whatsapp_desk.download_manager.Gtk") as mock_gtk:
            dm._on_download_finished(mock_download)

        # Verificar que se limpió el diccionario de descargas activas
        self.assertNotIn(mock_download, dm._active_downloads)

        # Verificar que restauró el título
        mock_window.set_title.assert_called_with("WhatsApp Desk")

        # Verificar que mostró notificación
        mock_alert = mock_gtk.AlertDialog.return_value
        mock_alert.set_message.assert_called_once_with("Descarga completada")
        mock_alert.show.assert_called_once_with(mock_window)

    @patch("whatsapp_desk.download_manager.GLib")
    def test_progress_updates_window_title(self, mock_glib):
        """El progreso de descarga actualiza el título de la ventana."""
        from whatsapp_desk.download_manager import DownloadManager

        mock_session = MagicMock()
        mock_window = MagicMock()
        dm = DownloadManager(mock_session, mock_window)

        mock_download = MagicMock()
        mock_download.get_estimated_progress.return_value = 0.75
        dm._active_downloads[mock_download] = "/tmp/foto.png"

        dm._on_progress_changed(mock_download, None)

        mock_window.set_title.assert_called_once_with(
            "WhatsApp Desk — foto.png (75%)"
        )

    @patch("whatsapp_desk.download_manager.GLib")
    def test_restore_title_only_when_no_active_downloads(self, mock_glib):
        """El título solo se restaura cuando no hay descargas activas pendientes."""
        from whatsapp_desk.download_manager import DownloadManager

        mock_session = MagicMock()
        mock_window = MagicMock()
        dm = DownloadManager(mock_session, mock_window)

        # Simular que aún hay una descarga activa
        mock_download_1 = MagicMock()
        mock_download_2 = MagicMock()
        dm._active_downloads[mock_download_1] = "/tmp/a.pdf"
        dm._active_downloads[mock_download_2] = "/tmp/b.pdf"

        # Finalizar solo una
        dm._on_download_failed(mock_download_1, MagicMock(code=400))
        # El título no debe restaurarse porque aún hay descargas activas
        mock_window.set_title.assert_not_called()


# ── Main ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
