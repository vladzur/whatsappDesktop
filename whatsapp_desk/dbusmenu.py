"""Implementación mínima del protocolo DBusMenu (com.canonical.dbusmenu).

El protocolo DBusMenu es el que usan los entornos de escritorio (GNOME Shell
con la extensión AppIndicator/KStatusNotifierItem, KDE Plasma, etc.) para
mostrar el menú contextual del icono de bandeja cuando el usuario hace clic
derecho.

Referencia: https://github.com/AyatanaIndicators/libdbusmenu/blob/master/libdbusmenu-glib/dbus-menu.xml

Uso básico
----------
    menu = DbusMenu(connection, "/DbusMenu", callbacks)
    # Luego indicar la ruta al SNI:  Menu = GLib.Variant("o", "/DbusMenu")
"""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gio  # noqa: E402

# ── Ruta D-Bus del objeto DBusMenu ───────────────────────────────────────────

DBUSMENU_PATH = "/DbusMenu"

# ── XML de introspección ─────────────────────────────────────────────────────

_DBUSMENU_XML = """
<node>
  <interface name="com.canonical.dbusmenu">

    <!-- Propiedades -->
    <property name="Version"       type="u" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="Status"        type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>

    <!-- Métodos principales -->
    <method name="GetLayout">
      <arg name="parentId"    type="i"  direction="in"/>
      <arg name="recursionDepth" type="i" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="revision"    type="u"  direction="out"/>
      <arg name="layout"      type="(ia{sv}av)" direction="out"/>
    </method>

    <method name="GetGroupProperties">
      <arg name="ids"           type="ai" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="properties"    type="a(ia{sv})" direction="out"/>
    </method>

    <method name="GetProperty">
      <arg name="id"       type="i"  direction="in"/>
      <arg name="name"     type="s"  direction="in"/>
      <arg name="value"    type="v"  direction="out"/>
    </method>

    <method name="Event">
      <arg name="id"        type="i" direction="in"/>
      <arg name="eventId"   type="s" direction="in"/>
      <arg name="data"      type="v" direction="in"/>
      <arg name="timestamp" type="u" direction="in"/>
    </method>

    <method name="EventGroup">
      <arg name="events"        type="a(isvu)" direction="in"/>
      <arg name="idErrors"      type="ai"      direction="out"/>
    </method>

    <method name="AboutToShow">
      <arg name="id"            type="i"  direction="in"/>
      <arg name="needUpdate"    type="b"  direction="out"/>
    </method>

    <method name="AboutToShowGroup">
      <arg name="ids"           type="ai" direction="in"/>
      <arg name="updatesNeeded" type="ai" direction="out"/>
      <arg name="idErrors"      type="ai" direction="out"/>
    </method>

    <!-- Señales -->
    <signal name="ItemsPropertiesUpdated">
      <arg name="updatedProps"  type="a(ia{sv})"/>
      <arg name="removedProps"  type="a(ias)"/>
    </signal>
    <signal name="LayoutUpdated">
      <arg name="revision" type="u"/>
      <arg name="parent"   type="i"/>
    </signal>
    <signal name="ItemActivationRequested">
      <arg name="id"        type="i"/>
      <arg name="timestamp" type="u"/>
    </signal>
  </interface>
</node>
"""

# ── Ítems del menú ───────────────────────────────────────────────────────────

# Cada ítem: (id, label, icon-name, separador)
# id=0  → raíz (siempre requerida por el protocolo)
# id>0  → ítem clicable
_SEPARATOR_ID = -1  # señal interna para separadores

_MENU_ITEMS = [
    # (id, label, icon)
    (1, "Abrir",  "view-restore-symbolic"),
    (2, "Ocultar", "window-minimize-symbolic"),
    (0, None, None),   # separador — id=0 se reusa, se detecta por label=None
    (3, "Salir",  "application-exit-symbolic"),
]


def _make_item_props(item_id: int, label, icon: str, is_separator: bool) -> dict:
    """Construye el dict de propiedades de un ítem DBusMenu."""
    if is_separator:
        return {"type": GLib.Variant("s", "separator")}
    props: dict = {
        "label":   GLib.Variant("s", label or ""),
        "enabled": GLib.Variant("b", True),
        "visible": GLib.Variant("b", True),
    }
    if icon:
        props["icon-name"] = GLib.Variant("s", icon)
    return props


# ── Clase principal ──────────────────────────────────────────────────────────

class DbusMenu:
    """Objeto D-Bus que implementa com.canonical.dbusmenu.

    Parameters
    ----------
    connection:
        Conexión de sesión D-Bus (``Gio.DBusConnection``).
    path:
        Ruta del objeto en el bus (default ``DBUSMENU_PATH``).
    on_show:
        Callable invocado cuando el usuario elige «Abrir».
    on_hide:
        Callable invocado cuando el usuario elige «Ocultar».
    on_quit:
        Callable invocado cuando el usuario elige «Salir».
    """

    def __init__(
        self,
        connection: Gio.DBusConnection,
        path: str = DBUSMENU_PATH,
        *,
        on_show=None,
        on_hide=None,
        on_quit=None,
    ):
        self._connection = connection
        self._path = path
        self._revision = 1
        self._reg_id = 0

        # Callbacks de acciones
        self._on_show = on_show
        self._on_hide = on_hide
        self._on_quit = on_quit

        # Construir árbol de ítems internamente
        # Separadores tienen label=None
        self._items: list[tuple[int, str | None, str | None, bool]] = []
        sep_counter = 100  # IDs para separadores (no activan callbacks)
        for entry in _MENU_ITEMS:
            item_id, label, icon = entry
            is_sep = label is None
            if is_sep:
                real_id = sep_counter
                sep_counter += 1
            else:
                real_id = item_id
            self._items.append((real_id, label, icon, is_sep))

        self._register()

    # ── D-Bus registration ───────────────────────────────────────────────

    def _register(self):
        """Registra el objeto DBusMenu en el bus de sesión."""
        try:
            node = Gio.DBusNodeInfo.new_for_xml(_DBUSMENU_XML)
            iface = node.interfaces[0]
            self._reg_id = self._connection.register_object(
                self._path,
                iface,
                self._handle_method,
                self._handle_get_prop,
                self._handle_set_prop,
            )
            if self._reg_id == 0:
                print("[DbusMenu] No se pudo registrar el objeto D-Bus")
        except Exception as exc:
            print(f"[DbusMenu] Error al registrar: {exc}")

    def cleanup(self):
        """Desregistra el objeto D-Bus."""
        if self._reg_id != 0:
            try:
                self._connection.unregister_object(self._reg_id)
            except Exception:
                pass
            self._reg_id = 0

    # ── Property handler ─────────────────────────────────────────────────

    def _handle_get_prop(self, connection, sender, obj_path, iface, key):
        props = {
            "Version":       GLib.Variant("u", 3),
            "TextDirection": GLib.Variant("s", "ltr"),
            "Status":        GLib.Variant("s", "normal"),
            "IconThemePath": GLib.Variant("as", []),
        }
        return props.get(key)

    def _handle_set_prop(self, connection, sender, obj_path, iface, key, value):
        return False  # solo lectura

    # ── Method handler ───────────────────────────────────────────────────

    def _handle_method(self, connection, sender, obj_path, iface,
                       method, params, invocation):
        try:
            if method == "GetLayout":
                self._get_layout(params, invocation)
            elif method == "GetGroupProperties":
                self._get_group_properties(params, invocation)
            elif method == "GetProperty":
                self._get_property(params, invocation)
            elif method == "Event":
                self._event(params, invocation)
            elif method == "EventGroup":
                self._event_group(params, invocation)
            elif method == "AboutToShow":
                invocation.return_value(GLib.Variant("(b)", (False,)))
            elif method == "AboutToShowGroup":
                invocation.return_value(GLib.Variant("(aiai)", ([], [])))
            else:
                invocation.return_value(None)
        except Exception as exc:
            print(f"[DbusMenu] Error en método {method}: {exc}")
            invocation.return_value(None)

    # ── GetLayout ────────────────────────────────────────────────────────

    def _build_item_variant(self, item_id: int, label, icon, is_sep: bool,
                            children: list) -> GLib.Variant:
        """Construye la variante (ia{sv}av) para un ítem."""
        props = _make_item_props(item_id, label, icon, is_sep)
        props_variant = GLib.Variant("a{sv}", props)
        children_variant = GLib.Variant("av", [
            GLib.Variant("v", c) for c in children
        ])
        return GLib.Variant("(ia{sv}av)", (item_id, props, children_variant))

    def _get_layout(self, params, invocation):
        parent_id, depth, _props = params.unpack()

        # Raíz: id=0, contiene todos los ítems
        children = []
        for (item_id, label, icon, is_sep) in self._items:
            child = self._build_item_variant(item_id, label, icon, is_sep, [])
            children.append(GLib.Variant("v", child))

        root_props: dict = {
            "children-display": GLib.Variant("s", "submenu"),
        }
        root = GLib.Variant(
            "(ia{sv}av)",
            (0, root_props, children),
        )
        invocation.return_value(GLib.Variant("(u(ia{sv}av))", (self._revision, root)))

    # ── GetGroupProperties ───────────────────────────────────────────────

    def _get_group_properties(self, params, invocation):
        ids, prop_names = params.unpack()
        result = []
        item_map = {item[0]: item for item in self._items}
        for item_id in ids:
            if item_id == 0:
                props = {"children-display": GLib.Variant("s", "submenu")}
            elif item_id in item_map:
                _, label, icon, is_sep = item_map[item_id]
                props = _make_item_props(item_id, label, icon, is_sep)
            else:
                props = {}
            result.append((item_id, props))
        invocation.return_value(GLib.Variant("(a(ia{sv}))", (result,)))

    # ── GetProperty ──────────────────────────────────────────────────────

    def _get_property(self, params, invocation):
        item_id, prop_name = params.unpack()
        item_map = {item[0]: item for item in self._items}
        if item_id in item_map:
            _, label, icon, is_sep = item_map[item_id]
            props = _make_item_props(item_id, label, icon, is_sep)
            value = props.get(prop_name, GLib.Variant("s", ""))
        else:
            value = GLib.Variant("s", "")
        invocation.return_value(GLib.Variant("(v)", (value,)))

    # ── Event (clic en ítem) ─────────────────────────────────────────────

    def _dispatch_action(self, item_id: int):
        """Ejecuta el callback correspondiente al ítem clicado."""
        if item_id == 1 and self._on_show:
            GLib.idle_add(self._on_show)
        elif item_id == 2 and self._on_hide:
            GLib.idle_add(self._on_hide)
        elif item_id == 3 and self._on_quit:
            GLib.idle_add(self._on_quit)

    def _event(self, params, invocation):
        item_id, event_id, _data, _timestamp = params.unpack()
        invocation.return_value(None)
        if event_id == "clicked":
            self._dispatch_action(item_id)

    def _event_group(self, params, invocation):
        events, = params.unpack()
        invocation.return_value(GLib.Variant("(ai)", ([],)))
        for (item_id, event_id, _data, _timestamp) in events:
            if event_id == "clicked":
                self._dispatch_action(item_id)
