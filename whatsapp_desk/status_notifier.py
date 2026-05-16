"""Implementación de StatusNotifierItem vía D-Bus directo.

Reemplaza a AyatanaAppIndicator3, que requiere GTK3 y es incompatible
con nuestra aplicación GTK4. Usa Gio.DBusConnection para registrar
un StatusNotifierItem en la bandeja del sistema.

Protocolo: org.kde.StatusNotifierItem (freedesktop.org)
"""

import os
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gio  # noqa: E402

# ── Constantes ──────────────────────────────────────────────────────────────

SNI_NAME_TEMPLATE = "org.kde.StatusNotifierItem-{pid}-{instance}"
SNI_PATH = "/StatusNotifierItem"

# Rutas de iconos
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ICON_SYMBOLIC_SRC = os.path.join(_PROJECT_ROOT, "whatsapp-desk-symbolic.svg")
_XDG_DATA = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
# appindicatorsupport espera la raíz del directorio de iconos XDG,
# NO la subdirectamente del tema (hicolor). El sufijo /hicolor lo añade
# internamente la extensión al buscar el icono por nombre.
_ICON_THEME_DIR = os.path.join(_XDG_DATA, "icons")
_ICON_INSTALL_DIR = os.path.join(_XDG_DATA, "icons", "hicolor", "scalable", "apps")
_ICON_SYMBOLIC_PATH = os.path.join(_ICON_INSTALL_DIR, "whatsapp-desk-symbolic.svg")

# XML de introspección D-Bus para org.kde.StatusNotifierItem
SNI_INTROSPECTION_XML = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <method name="Activate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="ContextMenu">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
      <arg name="menu" type="o" direction="out"/>
    </method>
    <method name="Scroll">
      <arg name="delta" type="i" direction="in"/>
      <arg name="orientation" type="s" direction="in"/>
    </method>
    <signal name="NewTitle"/>
    <signal name="NewIcon"/>
    <signal name="NewOverlayIcon"/>
    <signal name="NewAttentionIcon"/>
    <signal name="NewStatus">
      <arg name="status" type="s"/>
    </signal>
    <signal name="NewIconThemePath">
      <arg name="path" type="s"/>
    </signal>
    <signal name="NewToolTip"/>
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="WindowId" type="i" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconThemePath" type="s" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="Menu" type="o" access="read"/>
  </interface>
</node>
"""


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

    Registra un objeto D-Bus que implementa org.kde.StatusNotifierItem.
    Compatible con la extensión de GNOME Shell AppIndicator Support.
    """

    def __init__(self, application, window):
        self._app = application
        self._window = window
        self._connection = None
        self._owner_id = 0
        self._registered = False

        _ensure_symbolic_icon_installed()
        self._init_dbus()

    def _init_dbus(self):
        """Registra el servicio y los objetos D-Bus."""
        try:
            self._connection = Gio.bus_get_sync(
                Gio.BusType.SESSION, None
            )

            # Construir la interfaz desde XML
            node = Gio.DBusNodeInfo.new_for_xml(SNI_INTROSPECTION_XML)
            interface_info = node.interfaces[0]

            # Registrar el objeto en el bus antes de pedir el nombre
            self._sni_reg_id = self._connection.register_object(
                SNI_PATH,
                interface_info,
                self._handle_method_call,
                self._handle_property_get,
                self._handle_property_set,
            )
            if self._sni_reg_id == 0:
                print("[SNI] No se pudo registrar objeto StatusNotifierItem")
                return

            # Registrar el nombre de bus; el callback name_acquired llama al Watcher
            self._owner_id = Gio.bus_own_name_on_connection(
                self._connection,
                _bus_name(),
                Gio.BusNameOwnerFlags.NONE,
                self._on_name_acquired,
                self._on_name_lost,
            )
            if self._owner_id == 0:
                print("[SNI] No se pudo registrar el nombre D-Bus")
                return

        except Exception as exc:
            print(f"[SNI] Error al inicializar: {exc}")

    def _register_with_watcher(self):
        """Notifica al StatusNotifierWatcher que existe este indicador.

        Este paso es OBLIGATORIO para que la extensión appindicatorsupport
        de GNOME Shell detecte y muestre el icono en la barra de estado.
        """
        try:
            self._connection.call_sync(
                "org.kde.StatusNotifierWatcher",       # dest
                "/StatusNotifierWatcher",              # object path
                "org.kde.StatusNotifierWatcher",       # interface
                "RegisterStatusNotifierItem",          # method
                GLib.Variant("(s)", (_bus_name(),)),   # args: bus name
                None,                                  # reply type
                Gio.DBusCallFlags.NONE,
                2000,                                  # timeout (ms)
                None,
            )
            self._registered = True
            print("[SNI] Icono de bandeja registrado en el Watcher correctamente")

            # Emitir NewIconThemePath para que appindicatorsupport recargue
            # el icono desde nuestro directorio de temas personalizado.
            self._connection.emit_signal(
                None,                                  # destination (broadcast)
                SNI_PATH,
                "org.kde.StatusNotifierItem",
                "NewIconThemePath",
                GLib.Variant("(s)", (_ICON_THEME_DIR,)),
            )
        except Exception as exc:
            # El Watcher puede no estar disponible (escritorio sin soporte SNI)
            print(f"[SNI] No se pudo registrar en el Watcher: {exc}")
            self._registered = False

    def _handle_method_call(self, connection, sender, object_path,
                            interface_name, method_name, parameters,
                            invocation):
        """Maneja llamadas a métodos D-Bus."""
        if method_name == "Activate":
            parameters.unpack()  # coordenadas x, y — no se usan
            self._on_activate()
            invocation.return_value(None)
        elif method_name == "SecondaryActivate":
            self._on_secondary_activate()
            invocation.return_value(None)
        elif method_name == "ContextMenu":
            invocation.return_value(GLib.Variant("(o)", ("/NO_DBUSMENU",)))
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
            # IconName debe ser el nombre del icono (sin ruta ni extensión),
            # NO la ruta completa. El protocolo SNI resuelve el icono por nombre
            # usando IconThemePath como directorio de búsqueda.
            "IconName": GLib.Variant("s", "whatsapp-desk-symbolic"),
            "IconThemePath": GLib.Variant("s", _ICON_THEME_DIR),
            "ItemIsMenu": GLib.Variant("b", False),
            "Menu": GLib.Variant("o", "/NO_DBUSMENU"),
        }
        return props.get(key)

    def _handle_property_set(self, connection, sender, object_path,
                             interface_name, key, value):
        """Propiedades de solo lectura."""
        return False

    def _on_name_acquired(self, connection, name):
        """Callback cuando se adquiere el nombre D-Bus.

        Este es el momento correcto para notificar al StatusNotifierWatcher,
        ya que el nombre de bus ya está disponible y el objeto D-Bus registrado.
        """
        print(f"[SNI] Nombre D-Bus adquirido: {name}")
        self._register_with_watcher()

    def _on_name_lost(self, connection, name):
        """Callback cuando se pierde el nombre D-Bus."""
        print("[SNI] Se perdió el nombre D-Bus — ¿otro icono ya está activo?")

    def _on_activate(self):
        """Callback de clic primario en el icono (toggle ventana)."""
        GLib.idle_add(self.toggle_window)

    def _on_secondary_activate(self):
        """Callback de clic secundario — cierra la aplicación."""
        GLib.idle_add(self._app.activate_action, "quit", None)

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
        if self._owner_id != 0:
            try:
                Gio.bus_unown_name(self._owner_id)
            except Exception:
                pass
            self._owner_id = 0
        self._registered = False
