"""Ventana principal de WhatsApp Desk."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, WebKit, Gio, GObject  # noqa: E402

from whatsapp_desk.webview import WhatsAppWebView
from whatsapp_desk.url_handler import UrlHandler
from whatsapp_desk.tray import TrayIcon
from whatsapp_desk.notifications import NotificationManager
from whatsapp_desk.dark_mode import DarkModeManager
from whatsapp_desk.constants import WHATSAPP_URL


class MainWindow(Gtk.ApplicationWindow):
    """Ventana principal con HeaderBar y WebView de WhatsApp."""

    def __init__(self, application):
        super().__init__(application=application)
        self._app = application
        self._config = application.config
        self._webview_manager = application.webview_manager
        self._webview = None
        self._spinner = None
        self._overlay = None

        self._setup_window()
        self._setup_headerbar()
        self._setup_webview()
        self._restore_geometry()

    def _setup_window(self):
        """Configura propiedades básicas de la ventana."""
        self.set_title("WhatsApp Desk")
        self.set_icon_name("whatsapp-desk")
        self.set_default_size(
            self._config.get("window_width"),
            self._config.get("window_height"),
        )
        if self._config.get("window_maximized"):
            self.maximize()
        self.connect("close-request", self._on_close_request)

    def _setup_headerbar(self):
        """Crea la HeaderBar con botones de acción."""
        header = Gtk.HeaderBar()
        header.set_title_widget(Gtk.Label(label="WhatsApp Desk"))

        # Botón de ocultar a bandeja
        hide_btn = Gtk.Button.new_from_icon_name("window-hide-symbolic")
        hide_btn.set_tooltip_text("Minimizar a la bandeja del sistema")
        hide_btn.connect("clicked", self._on_hide_to_tray)
        header.pack_start(hide_btn)

        # Botón de recarga
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Recargar WhatsApp Web")
        refresh_btn.connect("clicked", self._on_refresh)
        header.pack_start(refresh_btn)

        # Menú de la aplicación
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_menu_model(self._build_menu())
        header.pack_end(menu_btn)

        # Botón de modo oscuro
        dark_btn = Gtk.Button.new_from_icon_name("display-brightness-symbolic")
        dark_btn.set_tooltip_text("Alternar modo oscuro")
        dark_btn.connect("clicked", self._on_toggle_dark_mode)
        header.pack_end(dark_btn)

        self.set_titlebar(header)

    def _build_menu(self) -> Gio.Menu:
        """Construye el menú de la aplicación."""
        menu = Gio.Menu()
        # Sección de archivo
        menu.append("Nueva ventana", "app.new-window")
        menu.append("Cerrar sesión", "app.clear-session")
        menu.append("Salir", "app.quit")
        return menu

    def _setup_webview(self):
        """Crea y configura el WebView de WhatsApp."""
        # Contenedor principal
        self._overlay = Gtk.Overlay()

        # Spinner de carga
        self._spinner = Gtk.Spinner()
        self._spinner.set_halign(Gtk.Align.CENTER)
        self._spinner.set_valign(Gtk.Align.CENTER)
        self._spinner.set_size_request(48, 48)
        self._overlay.add_overlay(self._spinner)

        # WebView
        network_session = self._webview_manager.get_network_session()
        self._webview = WhatsAppWebView(network_session=network_session)

        # Conectar señales de carga
        self._webview.connect("load-changed", self._on_load_changed)
        self._webview.connect("notify::title", self._on_title_changed)
        self._webview.connect("web-process-terminated", self._on_web_process_terminated)

        # Manejar enlaces externos
        self._url_handler = UrlHandler(self._webview)

        # Bandeja del sistema
        self._tray = TrayIcon(self._app, self)

        # Notificaciones de escritorio
        self._notifications = NotificationManager(self._webview, self._config)

        # Modo oscuro
        self._dark_mode = DarkModeManager(self._webview, self._config)

        self._overlay.set_child(self._webview)
        self.set_child(self._overlay)

        # Cargar WhatsApp Web
        self._webview.load_whatsapp()

        # Configurar atajos de teclado básicos (Ctrl+Q, Ctrl+R, etc.)
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """Registra atajos de teclado básicos."""
        controller = Gtk.ShortcutController()
        self.add_controller(controller)

        # Ctrl+W: Minimizar a bandeja
        trigger = Gtk.ShortcutTrigger.parse_string("<Control>w")
        action = Gtk.CallbackAction.new(self._on_hide_to_tray_shortcut)
        controller.add_shortcut(Gtk.Shortcut.new(trigger=trigger, action=action))

        # Ctrl+Q: Salir
        trigger = Gtk.ShortcutTrigger.parse_string("<Control>q")
        action = Gtk.CallbackAction.new(lambda w, a: self.close())
        controller.add_shortcut(Gtk.Shortcut.new(trigger=trigger, action=action))

        # Ctrl+R: Recargar
        trigger = Gtk.ShortcutTrigger.parse_string("<Control>r")
        action = Gtk.CallbackAction.new(self._on_refresh_shortcut)
        controller.add_shortcut(Gtk.Shortcut.new(trigger=trigger, action=action))

        # F5: Recargar
        trigger = Gtk.ShortcutTrigger.parse_string("F5")
        action = Gtk.CallbackAction.new(self._on_refresh_shortcut)
        controller.add_shortcut(Gtk.Shortcut.new(trigger=trigger, action=action))

        # F11: Pantalla completa
        trigger = Gtk.ShortcutTrigger.parse_string("F11")
        action = Gtk.CallbackAction.new(self._on_toggle_fullscreen)
        controller.add_shortcut(Gtk.Shortcut.new(trigger=trigger, action=action))

        # Escape: Salir de pantalla completa
        trigger = Gtk.ShortcutTrigger.parse_string("Escape")
        action = Gtk.CallbackAction.new(self._on_exit_fullscreen)
        controller.add_shortcut(Gtk.Shortcut.new(trigger=trigger, action=action))

        # Ctrl+plus: Zoom in
        trigger = Gtk.ShortcutTrigger.parse_string("<Control>equal")
        action = Gtk.CallbackAction.new(self._on_zoom_in)
        controller.add_shortcut(Gtk.Shortcut.new(trigger=trigger, action=action))

        # Ctrl+minus: Zoom out
        trigger = Gtk.ShortcutTrigger.parse_string("<Control>minus")
        action = Gtk.CallbackAction.new(self._on_zoom_out)
        controller.add_shortcut(Gtk.Shortcut.new(trigger=trigger, action=action))

        # Ctrl+0: Reset zoom
        trigger = Gtk.ShortcutTrigger.parse_string("<Control>0")
        action = Gtk.CallbackAction.new(self._on_zoom_reset)
        controller.add_shortcut(Gtk.Shortcut.new(trigger=trigger, action=action))

    # ── Callbacks de WebView ──────────────────────────────────────────────

    def _on_load_changed(self, webview, load_event):
        """Actualiza el spinner según el estado de carga."""
        if load_event == WebKit.LoadEvent.STARTED:
            self._spinner.start()
            self._spinner.set_visible(True)
        elif load_event == WebKit.LoadEvent.FINISHED:
            self._spinner.stop()
            self._spinner.set_visible(False)

    def _on_title_changed(self, webview, param):
        """Actualiza el título de la ventana cuando cambia el título de la página."""
        title = webview.get_property("title")
        if title:
            self.set_title(title)

    def _on_web_process_terminated(self, webview, reason):
        """Maneja la terminación inesperada del proceso web."""
        if reason == WebKit.WebProcessTerminationReason.CRASHED:
            dialog = Gtk.AlertDialog()
            dialog.set_message("WhatsApp Web ha fallado")
            dialog.set_detail(
                "El proceso de WebKit ha terminado inesperadamente. "
                "¿Quieres recargar la página?"
            )
            dialog.set_buttons(["Recargar", "Cancelar"])
            dialog.set_default_button(0)
            dialog.set_cancel_button(1)
            dialog.show(self)

    # ── Callbacks de acciones ─────────────────────────────────────────────

    def _on_refresh(self, button):
        """Recarga WhatsApp Web."""
        self._webview.reload()

    def _on_refresh_shortcut(self, widget, shortcut):
        self._webview.reload()

    def _on_hide_to_tray_shortcut(self, widget, shortcut):
        self.hide_to_tray()

    def _on_hide_to_tray(self, button):
        """Minimiza la ventana a la bandeja del sistema."""
        self.hide_to_tray()

    def _on_toggle_dark_mode(self, button):
        """Alterna el modo oscuro."""
        self._dark_mode.toggle()

    def _on_toggle_fullscreen(self, widget, shortcut):
        self.fullscreen()

    def _on_exit_fullscreen(self, widget, shortcut):
        if self.is_fullscreen():
            self.unfullscreen()

    def _on_zoom_in(self, widget, shortcut):
        current = self._webview.get_zoom_level()
        self._webview.set_zoom_level(min(current + 0.1, 3.0))

    def _on_zoom_out(self, widget, shortcut):
        current = self._webview.get_zoom_level()
        self._webview.set_zoom_level(max(current - 0.1, 0.3))

    def _on_zoom_reset(self, widget, shortcut):
        self._webview.set_zoom_level(1.0)

    def _on_close_request(self, window):
        """Decide si cerrar la ventana o minimizar a la bandeja."""
        # Minimizar a bandeja si está habilitado y disponible
        if self._config.get("close_to_tray") and self._tray.is_available():
            self.hide()
            return True  # True = prevenir cierre de ventana
        self.save_geometry()
        return False  # False = permitir cierre

    # ── Geometría de ventana ──────────────────────────────────────────────

    def save_geometry(self):
        """Guarda el tamaño y estado de la ventana."""
        maximized = self.is_maximized()
        self._config.set("window_maximized", maximized)
        if not maximized:
            width, height = self.get_default_size()
            self._config.set("window_width", width)
            self._config.set("window_height", height)

    def _restore_geometry(self):
        """Restaura el tamaño guardado de la ventana."""
        pass  # Ya se aplica en _setup_window con set_default_size

    def hide_to_tray(self):
        """Oculta la ventana al área de notificación."""
        self.hide()

    def replace_webview(self):
        """Recrea el WebView con una nueva sesión de red (útil tras clear_session)."""
        # Eliminar WebView antiguo
        old_webview = self._webview
        self._overlay.set_child(None)

        # Crear nuevo WebView con nueva sesión
        network_session = self._webview_manager.get_network_session()
        self._webview = WhatsAppWebView(network_session=network_session)

        # Reconectar señales
        self._webview.connect("load-changed", self._on_load_changed)
        self._webview.connect("notify::title", self._on_title_changed)
        self._webview.connect("web-process-terminated", self._on_web_process_terminated)

        # Reconectar handler de enlaces externos
        self._url_handler = UrlHandler(self._webview)

        # Recrear notificaciones
        self._notifications = NotificationManager(self._webview, self._config)

        # Establecer en el overlay y cargar
        self._overlay.set_child(self._webview)
        self._webview.load_whatsapp()

        # Destruir el viejo WebView
        old_webview.destroy()
