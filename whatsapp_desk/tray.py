"""Integración con la bandeja del sistema vía AyatanaAppIndicator3."""

import gi

TRAY_AVAILABLE = False

try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    # Verificar que la biblioteca carga correctamente
    from gi.repository import AyatanaAppIndicator3 as AppIndicator  # noqa: E402
    from gi.repository import Gio  # noqa: E402

    TRAY_AVAILABLE = True
except (ValueError, ImportError, RuntimeError):
    pass


class TrayIcon:
    """Icono en la bandeja del sistema con menú contextual.

    Permite ocultar/mostrar la ventana y salir de la aplicación.
    Si la biblioteca AppIndicator no está disponible, se desactiva
    silenciosamente.
    """

    def __init__(self, application, window):
        self._app = application
        self._window = window
        self._indicator = None

        if TRAY_AVAILABLE:
            self._create_indicator()

    def _create_indicator(self):
        """Crea el indicador AppIndicator y su menú."""
        try:
            self._indicator = AppIndicator.Indicator.new(
                "whatsapp-desk",
                "whatsapp-desk-symbolic",
                AppIndicator.IndicatorCategory.APPLICATION_STATUS,
            )
            self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            self._indicator.set_title("WhatsApp Desk")

            # Gio.Menu como modelo de menú (soportado por AppIndicator 0.5+)
            menu = self._build_menu()
            self._indicator.set_menu(menu)
        except Exception:
            self._indicator = None

    def _build_menu(self):
        """Construye el menú Gio.Menu para el icono de bandeja."""
        menu = Gio.Menu()

        show_item = Gio.MenuItem.new("Mostrar ventana", "app.show-window")
        menu.append_item(show_item)

        quit_item = Gio.MenuItem.new("Salir", "app.quit")
        menu.append_item(quit_item)

        return menu

    def toggle_window(self):
        """Muestra u oculta la ventana principal."""
        if self._window.is_visible():
            self._window.hide()
        else:
            self._window.present()

    def show_window(self):
        """Muestra la ventana principal."""
        self._window.present()

    def is_available(self) -> bool:
        """Indica si la funcionalidad de bandeja está disponible."""
        return self._indicator is not None
