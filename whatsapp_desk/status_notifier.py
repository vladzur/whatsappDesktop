"""Implementación de StatusNotifierItem vía D-Bus directo.

Reemplaza a AyatanaAppIndicator3, que requiere GTK3 y es incompatible
con nuestra aplicación GTK4. Usa Gio.DBusConnection para registrar
un StatusNotifierItem en la bandeja del sistema.

Protocolo: org.kde.StatusNotifierItem (freedesktop.org)

Badge de mensajes no leídos
---------------------------
Cuando hay mensajes sin leer se cambia ``IconName`` al icono
``whatsapp-desk-unread-symbolic`` y se emite la señal D-Bus ``NewIcon``.
Ese icono se genera en tiempo de ejecución (SVG inline) la primera vez.
"""

import os
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gio  # noqa: E402

# ── Constantes ──────────────────────────────────────────────────────────────

SNI_NAME_TEMPLATE = "org.kde.StatusNotifierItem-{pid}-{instance}"
SNI_PATH = "/StatusNotifierItem"

# Rutas de iconos desde el módulo central de constantes
from whatsapp_desk.constants import (  # noqa: E402
    IN_FLATPAK,
    ICON_DIR,
    ICON_SRC_DIR,
    ICON_THEME_DIR,
)

_ICON_SYMBOLIC_SRC = os.path.join(ICON_SRC_DIR, "whatsapp-desk-symbolic.svg")
_ICON_SYMBOLIC_PATH = os.path.join(ICON_DIR, "whatsapp-desk-symbolic.svg")
_ICON_UNREAD_PATH = os.path.join(ICON_DIR, "whatsapp-desk-unread-symbolic.svg")

# Nombre de los iconos (sin ruta ni extensión — protocolo SNI los resuelve por nombre)
_ICON_NORMAL = "whatsapp-desk-symbolic"
_ICON_UNREAD = "whatsapp-desk-unread-symbolic"

# SVG del icono con badge: mismo diseño base + círculo de notificación verde
_ICON_UNREAD_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">
  <!-- Burbuja de chat con forma de teléfono — diseño symbolic monocromático -->
  <!-- NOTA: usa currentColor para que se adapte al tema del panel de GNOME -->
  <g fill="currentColor">
    <!-- Cuerpo del teléfono/burbuja -->
    <path d="M1 2 L1 12 C1 13.1 1.9 14 3 14 L10 14 L12 16 L12 14 L13 14 C14.1 14 15 13.1 15 12 L15 2 C15 0.9 14.1 0 13 0 L3 0 C1.9 0 1 0.9 1 2 Z"/>
    <!-- Auricular del teléfono -->
    <path d="M5 5 C5 5 4.5 6 5.5 7.5 C6.5 9 7.5 9.5 7.5 9.5 C7.5 9.5 6 11 6.5 12 C7 13 8.5 13 9.5 11.5 C10.5 10 10 8 8.5 7 C7 6 5 5 5 5 Z" opacity="0.5"/>
  </g>
  <!-- Badge de notificación: círculo rojo en la esquina superior derecha -->
  <circle cx="13" cy="3" r="3" fill="#e74c3c" stroke="none"/>
</svg>
"""

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
    """Copia el icono symbolic al directorio de iconos del usuario.

    En Flatpak los iconos ya están preinstalados en /app/share/icons/.
    """
    if IN_FLATPAK:
        return
    if not os.path.isfile(_ICON_SYMBOLIC_SRC):
        return
    try:
        os.makedirs(ICON_DIR, exist_ok=True)
        if not os.path.isfile(_ICON_SYMBOLIC_PATH):
            import shutil
            shutil.copy2(_ICON_SYMBOLIC_SRC, _ICON_SYMBOLIC_PATH)
    except OSError:
        pass


def _ensure_unread_icon_installed():
    """Crea el icono con badge de notificación si no existe.

    En Flatpak los iconos ya están preinstalados en /app/share/icons/.
    """
    if IN_FLATPAK:
        return
    try:
        os.makedirs(ICON_DIR, exist_ok=True)
        if not os.path.isfile(_ICON_UNREAD_PATH):
            with open(_ICON_UNREAD_PATH, "w", encoding="utf-8") as f:
                f.write(_ICON_UNREAD_SVG)
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

    Badge de mensajes no leídos
    ---------------------------
    Llama a ``set_unread(count)`` para mostrar el icono de alerta y a
    ``clear_unread()`` cuando el usuario abre la ventana.
    """

    def __init__(self, application, window):
        self._app = application
        self._window = window
        self._connection = None
        self._owner_id = 0
        self._registered = False
        self._current_icon = _ICON_NORMAL   # nombre de icono activo

        _ensure_symbolic_icon_installed()
        _ensure_unread_icon_installed()
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
            # IconName se sirve dinámicamente desde self._current_icon
            # para reflejar el estado de mensajes no leídos.
            "IconName": GLib.Variant("s", self._current_icon),
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

    # ── Badge de mensajes no leídos ──────────────────────────────────────

    def set_unread(self, count: int):
        """Cambia el icono al estado 'con badge' cuando hay mensajes sin leer.

        Parameters
        ----------
        count:
            Número de mensajes sin leer. Si es 0 se llama a ``clear_unread``.
        """
        if count <= 0:
            self.clear_unread()
            return
        if self._current_icon == _ICON_UNREAD:
            return  # ya está en estado de badge — evitar señales redundantes
        self._current_icon = _ICON_UNREAD
        self._emit_new_icon()

    def clear_unread(self):
        """Restaura el icono al estado normal (sin badge)."""
        if self._current_icon == _ICON_NORMAL:
            return  # ya en estado normal
        self._current_icon = _ICON_NORMAL
        self._emit_new_icon()

    def _emit_new_icon(self):
        """Emite la señal D-Bus NewIcon para que appindicatorsupport recargue el icono."""
        if not self._registered or self._connection is None:
            return
        try:
            self._connection.emit_signal(
                None,
                SNI_PATH,
                "org.kde.StatusNotifierItem",
                "NewIcon",
                None,
            )
        except Exception as exc:
            print(f"[SNI] Error al emitir NewIcon: {exc}")

    # ── Estado ────────────────────────────────────────────────────────────

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
