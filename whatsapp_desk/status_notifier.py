"""Implementación de StatusNotifierItem vía D-Bus directo.

Reemplaza a AyatanaAppIndicator3, que requiere GTK3 y es incompatible
con nuestra aplicación GTK4. Usa Gio.DBusConnection para registrar
un StatusNotifierItem + menú com.canonical.dbusmenu en la bandeja.
"""

import os
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gio  # noqa: E402

# ── Constantes ──────────────────────────────────────────────────────────────

SNI_NAME_TEMPLATE = "org.kde.StatusNotifierItem-{pid}-{instance}"
SNI_PATH = "/StatusNotifierItem"
SNI_INTERFACE = "org.kde.StatusNotifierItem"

# Ruta al icono symbolic para la bandeja
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ICON_SYMBOLIC_SRC = os.path.join(_PROJECT_ROOT, "whatsapp-desk-symbolic.svg")
_ICON_INSTALL_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "icons",
    "hicolor",
    "scalable",
    "apps",
)
_ICON_SYMBOLIC_PATH = os.path.join(_ICON_INSTALL_DIR, "whatsapp-desk-symbolic.svg")


def _ensure_symbolic_icon_installed():
    """Copia el icono symbolic al directorio de iconos del usuario."""
    if not os.path.isfile(_ICON_SYMBOLIC_SRC):
        return
    try:
        os.makedirs(_ICON_INSTALL_DIR, exist_ok=True)
        if not os.path.isfile(_ICON_SYMBOLIC_PATH):
            import shutil
            shutil.copy2(_ICON_SYMBOLIC_SRC, _ICON_SYMBOLIC_PATH)
    except OSError:
        pass


def _pid():
    return os.getpid()


def _bus_name(instance=1):
    return SNI_NAME_TEMPLATE.format(pid=_pid(), instance=instance)


class StatusNotifierItem:
    """Icono en la bandeja del sistema usando el protocolo StatusNotifierItem.

    Registra un objeto D-Bus que implementa org.kde.StatusNotifierItem
    con un menú contextual com.canonical.dbusmenu. Compatible con la
    extensión de GNOME Shell AppIndicator Support.
    """

    def __init__(self, application, window):
        self._app = application
        self._window = window
        self._connection = None
        self._registered = False
        self._menu_node_id = None
        self._next_menu_item_id = 0

        _ensure_symbolic_icon_installed()
        self._init_dbus()

    def _init_dbus(self):
        """Registra el servicio y los objetos D-Bus."""
        try:
            self._connection = Gio.DBusConnection.session()

            # Registrar el nombre de bus
            owner_id = self._connection.own_name(
                _bus_name(),
                flags=Gio.BusNameOwnerFlags.NONE,
                name_acquired_handler=None,
                name_lost_handler=self._on_name_lost,
            )
            if owner_id == 0:
                print("[SNI] No se pudo registrar el nombre D-Bus")
                return

            # Registrar el objeto StatusNotifierItem
            self._sni_reg_id = self._connection.register_object(
                SNI_PATH,
                self._build_sni_info(),
                self._handle_method_call,
                self._handle_property_get,
                self._handle_property_set,
            )
            if self._sni_reg_id == 0:
                print("[SNI] No se pudo registrar objeto StatusNotifierItem")
                return

            self._registered = True
            print("[SNI] Icono de bandeja registrado correctamente")
        except Exception as exc:
            print(f"[SNI] Error al inicializar: {exc}")

    def _build_sni_info(self):
        """Construye el Gio.DBusInterfaceInfo para StatusNotifierItem."""
        # org.kde.StatusNotifierItem
        method_new_title = Gio.DBusMethodInfo(
            name="NewTitle",
            in_args=[],
            out_args=[],
        )
        method_new_icon = Gio.DBusMethodInfo(
            name="NewIcon",
            in_args=[],
            out_args=[],
        )
        method_new_status = Gio.DBusMethodInfo(
            name="NewStatus",
            in_args=[Gio.DBusArgInfo(name="status", signature="s", ref_count=0)],
            out_args=[],
        )
        signal_new_icon_theme = Gio.DBusSignalInfo(
            name="NewIconThemePath",
            args=[Gio.DBusArgInfo(name="path", signature="s", ref_count=0)],
        )
        prop_category = Gio.DBusPropertyInfo(
            name="Category", signature="s", flags=Gio.DBusPropertyInfoFlags.READABLE
        )
        prop_id = Gio.DBusPropertyInfo(
            name="Id", signature="s", flags=Gio.DBusPropertyInfoFlags.READABLE
        )
        prop_title = Gio.DBusPropertyInfo(
            name="Title", signature="s", flags=Gio.DBusPropertyInfoFlags.READABLE
        )
        prop_status = Gio.DBusPropertyInfo(
            name="Status", signature="s", flags=Gio.DBusPropertyInfoFlags.READABLE
        )
        prop_window_id = Gio.DBusPropertyInfo(
            name="WindowId", signature="i", flags=Gio.DBusPropertyInfoFlags.READABLE
        )
        prop_icon_name = Gio.DBusPropertyInfo(
            name="IconName", signature="s", flags=Gio.DBusPropertyInfoFlags.READABLE
        )
        prop_icon_theme_path = Gio.DBusPropertyInfo(
            name="IconThemePath", signature="s", flags=Gio.DBusPropertyInfoFlags.READABLE
        )
        prop_item_is_menu = Gio.DBusPropertyInfo(
            name="ItemIsMenu", signature="b", flags=Gio.DBusPropertyInfoFlags.READABLE
        )
        prop_menu = Gio.DBusPropertyInfo(
            name="Menu", signature="o", flags=Gio.DBusPropertyInfoFlags.READABLE
        )

        sni_iface = Gio.DBusInterfaceInfo(
            name=SNI_INTERFACE,
            methods=[method_new_title, method_new_icon, method_new_status],
            signals=[signal_new_icon_theme],
            properties=[
                prop_category, prop_id, prop_title, prop_status,
                prop_window_id, prop_icon_name, prop_icon_theme_path,
                prop_item_is_menu, prop_menu,
            ],
        )

        node = Gio.DBusNodeInfo.new_xml(
            "<node>"
            '  <interface name="org.kde.StatusNotifierItem">'
            '    <method name="Activate"><arg name="x" direction="in" type="i"/><arg name="y" direction="in" type="i"/></method>'
            '    <method name="SecondaryActivate"><arg name="x" direction="in" type="i"/><arg name="y" direction="in" type="i"/></method>'
            '    <method name="ContextMenu"><arg name="x" direction="in" type="i"/><arg name="y" direction="in" type="i"/><arg name="menu" direction="out" type="o"/></method>'
            '    <method name="Scroll"><arg name="delta" direction="in" type="i"/><arg name="orientation" direction="in" type="s"/></method>'
            '    <property name="Category" type="s" access="read"/>'
            '    <property name="Id" type="s" access="read"/>'
            '    <property name="Title" type="s" access="read"/>'
            '    <property name="Status" type="s" access="read"/>'
            '    <property name="WindowId" type="i" access="read"/>'
            '    <property name="IconName" type="s" access="read"/>'
            '    <property name="IconThemePath" type="s" access="read"/>'
            '    <property name="ItemIsMenu" type="b" access="read"/>'
            '    <property name="Menu" type="o" access="read"/>'
            "  </interface>"
            "</node>"
        )

        return node.interfaces[0]

    def _handle_method_call(self, connection, sender, object_path,
                            interface_name, method_name, parameters,
                            invocation):
        """Maneja llamadas a métodos D-Bus."""
        if method_name == "Activate":
            x, y = parameters.unpack()
            self._on_activate()
            invocation.return_value(None)
        elif method_name == "SecondaryActivate":
            self._on_secondary_activate()
            invocation.return_value(None)
        elif method_name == "ContextMenu":
            menu_path = self._get_or_create_menu()
            invocation.return_value(GLib.Variant("(o)", (menu_path,)))
        elif method_name == "Scroll":
            invocation.return_value(None)
        else:
            invocation.return_value(None)

    def _handle_property_get(self, connection, sender, object_path,
                             interface_name, key):
        """Devuelve el valor de una propiedad D-Bus."""
        props = {
            "Category": GLib.Variant("s", "ApplicationStatus"),
            "Id": GLib.Variant("s", "whatsapp-desk"),
            "Title": GLib.Variant("s", "WhatsApp Desk"),
            "Status": GLib.Variant("s", "Active"),
            "WindowId": GLib.Variant("i", 0),
            "IconName": GLib.Variant("s", "whatsapp-desk-symbolic"),
            "IconThemePath": GLib.Variant("s", ""),
            "ItemIsMenu": GLib.Variant("b", False),
            "Menu": GLib.Variant("o", "/NO_DBUSMENU"),
        }
        return props.get(key)

    def _handle_property_set(self, connection, sender, object_path,
                             interface_name, key, value):
        """Maneja escritura de propiedades (no soportado)."""
        return False

    def _on_name_lost(self, connection, name):
        """Callback cuando se pierde el nombre D-Bus."""
        print("[SNI] Se perdió el nombre D-Bus, puede que otro icono esté activo")

    def _on_activate(self):
        """Callback de clic primario en el icono."""
        GLib.idle_add(self.toggle_window)

    def _on_secondary_activate(self):
        """Callback de clic secundario en el icono."""
        pass  # El menú contextual se maneja vía ContextMenu

    def _get_or_create_menu(self):
        """Crea un menú D-Bus simple si no existe."""
        # La mayoría de las implementaciones de bandeja en GNOME
        # no soportan dbusmenu completo. Devolvemos /NO_DBUSMENU
        # y en su lugar usamos Activate para toggle.
        return "/NO_DBUSMENU"

    def toggle_window(self):
        """Muestra u oculta la ventana principal."""
        try:
            if self._window.is_visible():
                self._window.hide()
            else:
                self._window.present()
        except Exception:
            pass

    def show_window(self):
        """Muestra la ventana principal."""
        GLib.idle_add(self._window.present)

    def is_available(self) -> bool:
        """Indica si el icono de bandeja está registrado."""
        return self._registered

    def cleanup(self):
        """Limpia recursos D-Bus al cerrar."""
        if self._connection:
            try:
                self._connection.unown_name(1)
            except Exception:
                pass
        self._registered = False
