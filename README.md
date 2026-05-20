# WhatsApp Desk

Aplicación de escritorio GNOME para WhatsApp Web. Construida con GTK 4, WebKit 6 y Python.

## Características

- Interfaz nativa GTK 4 / GNOME
- Icono en el Dock (dash-to-dock) y en la barra de estado (tray)
- Modo oscuro
- Notificaciones de escritorio
- Persistencia de sesión (no cierra sesión al cerrar la ventana)
- Minimizar a la bandeja con Ctrl+W

---

## Requisitos del sistema

| Paquete | Propósito |
|---------|-----------|
| `python3` (≥ 3.10) | Intérprete |
| `python3-gi` | Bindings PyGObject (GTK, GLib, Gio…) |
| `python3-gi-cairo` | Soporte Cairo para PyGObject |
| `gir1.2-gtk-4.0` | GTK 4 typelib |
| `gir1.2-webkit2-6.0` ó `gir1.2-webkitgtk-6.0` | WebKit 6 typelib |

```bash
# Ubuntu / Debian (una sola línea):
sudo apt install python3 python3-gi python3-gi-cairo \
    gir1.2-gtk-4.0 gir1.2-webkit2-6.0 libgtk-4-bin
```

### Extensión GNOME (para el icono en el tray)

La extensión **AppIndicator and KStatusNotifierItem Support** es necesaria para que el icono aparezca en la barra de estado de GNOME Shell.

```bash
# Instalar desde paquete del sistema:
sudo apt install gnome-shell-extension-appindicator

# O desde la tienda de extensiones:
# https://extensions.gnome.org/extension/615/

# Activar:
gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com
```

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repo> ~/MisProyectos/whatsappDesk
cd ~/MisProyectos/whatsappDesk

# 2. Verificar dependencias
./install.sh --check

# 3. Instalar
./install.sh
```

> **Nota:** La instalación es local para el usuario (no requiere `sudo`).  
> Los archivos se instalan en `~/.local/`.

### Usando Make

```bash
make check    # verificar dependencias
make install  # instalar
make run      # lanzar directamente desde el proyecto (sin instalar)
make test     # ejecutar tests
make uninstall  # desinstalar
```

---

## Desinstalación

```bash
./uninstall.sh
# o
make uninstall
```

Los datos de sesión (`~/.local/share/whatsapp-desk`) y la configuración (`~/.config/whatsapp-desk`) **no se eliminan** automáticamente. Para borrarlos también:

```bash
rm -rf ~/.local/share/whatsapp-desk ~/.config/whatsapp-desk
```

---

## Empaquetado Flatpak

Para distribuir la aplicación a otros equipos sin necesidad de instalar dependencias manualmente.

### Requisitos

```bash
# Ubuntu / Debian
sudo apt install flatpak flatpak-builder

# Añadir Flathub (si no está configurado)
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

El script de build instala automáticamente el runtime `org.gnome.Platform/x86_64/49` si no está presente.

### Construir e instalar localmente

```bash
./build-aux/build.sh
```

Esto ejecuta tres pasos:

1. **`flatpak-builder`** — compila e instala la app en el repositorio local del usuario
2. **`flatpak build-export`** — exporta el build al repositorio
3. **`flatpak build-bundle`** — genera el archivo portable `whatsapp-desk.flatpak`

### Probar la app sin instalar en el sistema

```bash
flatpak-builder --user --install .flatpak-build build-aux/com.vladzur.WhatsAppDesk.json
flatpak run com.vladzur.WhatsAppDesk
```

### Instalar desde el bundle en otro equipo

```bash
flatpak install --user whatsapp-desk.flatpak
flatpak run com.vladzur.WhatsAppDesk
```

### Desinstalar la versión Flatpak

```bash
flatpak uninstall --user com.vladzur.WhatsAppDesk
```

### Permisos del sandbox

El manifiesto solicita los siguientes permisos:

| Permiso | Motivo |
|---------|--------|
| `--socket=wayland --socket=fallback-x11` | Interfaz gráfica |
| `--socket=pulseaudio` | Audio para notificaciones |
| `--share=network` | Conexión a WhatsApp Web |
| `--device=dri` | Aceleración GPU (WebKit) |
| `--filesystem=xdg-download` | Descarga de archivos |
| `--talk-name=org.kde.StatusNotifierWatcher` | Icono en la bandeja del sistema |
| `--talk-name=org.freedesktop.Notifications` | Notificaciones de escritorio |

### Notas sobre el icono de bandeja en Flatpak

- Los iconos usan nombres RDNN (`com.vladzur.WhatsAppDesk-symbolic`) para que Flatpak los exporte correctamente al host.
- La app detecta automáticamente si se ejecuta dentro del sandbox y adapta las respuestas D-Bus (`IconThemePath` vacío) para que GNOME Shell resuelva los iconos vía `XDG_DATA_DIRS`.
- La extensión **AppIndicator Support** sigue siendo necesaria en el equipo anfitrión.

---

## Estructura del proyecto

```
whatsappDesk/
├── install.sh                 # Script de instalación
├── uninstall.sh               # Script de desinstalación
├── Makefile                   # Comandos de desarrollo
├── setup.py                   # Metadatos del paquete Python
├── whatsapp_desk.desktop.in   # Plantilla del archivo .desktop
├── whatsapp-desk.svg          # Icono de la aplicación
├── whatsapp-desk-symbolic.svg # Icono simbólico (tray)
├── whatsapp_desk/             # Código fuente Python
│   ├── application.py         # Punto de entrada GTK Application
│   ├── main_window.py         # Ventana principal
│   ├── status_notifier.py     # Icono de bandeja (SNI via D-Bus)
│   ├── tray.py                # Wrapper de bandeja (AppIndicator3)
│   ├── webview.py             # WebView de WhatsApp
│   ├── webview_manager.py     # Gestión de la sesión de red
│   ├── notifications.py       # Notificaciones de escritorio
│   ├── dark_mode.py           # Modo oscuro
│   ├── url_handler.py         # Manejo de enlaces externos
│   ├── config.py              # Configuración persistente
│   └── constants.py           # Constantes globales
└── tests/                     # Tests unitarios
```

---

## Notas técnicas

- **D-Bus / Tray:** La app implementa el protocolo `org.kde.StatusNotifierItem` directamente vía `Gio.DBusConnection`, compatible con la extensión `appindicatorsupport@rgcjonas.gmail.com`.
- **Icono en el Dock:** El archivo `.desktop` incluye `StartupWMClass=com.vladzur.WhatsAppDesk` para que GNOME Shell asocie correctamente la ventana GTK con el lanzador.
- **Icono simbólico:** El SVG usa `fill="currentColor"` para adaptarse automáticamente al tema claro/oscuro del panel.
