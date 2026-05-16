#!/usr/bin/env bash
# ============================================================
# WhatsApp Desk — Script de instalación para usuario local
# ============================================================
# Uso:
#   ./install.sh          → instalar
#   ./install.sh --check  → verificar dependencias sin instalar
#
# Requisitos del sistema:
#   - Python 3.10+
#   - python3-gi (PyGObject)
#   - gir1.2-gtk-4.0
#   - gir1.2-webkit2-6.0  (o gir1.2-webkit-6.0)
#   - gir1.2-glib-2.0
#   - GNOME Shell con extensión appindicatorsupport (para el tray)
# ============================================================

set -euo pipefail

# ── Colores ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

ok()   { echo -e "${GREEN}✔${NC}  $*"; }
info() { echo -e "${BLUE}ℹ${NC}  $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "${RED}✘${NC}  $*" >&2; }
die()  { err "$*"; exit 1; }

# ── Directorio del proyecto (ruta real del script) ───────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

# ── Rutas de destino ─────────────────────────────────────────
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

APPS_DIR="$XDG_DATA_HOME/applications"
ICON_DIR="$XDG_DATA_HOME/icons/hicolor/scalable/apps"
BIN_DIR="$HOME/.local/bin"

DESKTOP_SRC="$PROJECT_DIR/whatsapp_desk.desktop.in"
DESKTOP_DST="$APPS_DIR/whatsapp-desk.desktop"
ICON_SRC="$PROJECT_DIR/whatsapp-desk.svg"
ICON_DST="$ICON_DIR/whatsapp-desk.svg"
ICON_SYM_SRC="$PROJECT_DIR/whatsapp-desk-symbolic.svg"
ICON_SYM_DST="$ICON_DIR/whatsapp-desk-symbolic.svg"
WRAPPER_DST="$BIN_DIR/whatsapp-desk"

# ── Función: verificar dependencias ──────────────────────────
check_deps() {
    local all_ok=true

    echo ""
    echo -e "${BOLD}Verificando dependencias del sistema...${NC}"
    echo "──────────────────────────────────────────"

    # Python 3.10+
    local python_bin=""
    for py in python3 python3.12 python3.11 python3.10; do
        if command -v "$py" &>/dev/null; then
            local ver
            ver=$("$py" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [[ "$major" -ge 3 && "$minor" -ge 10 ]]; then
                ok "Python $ver ($py)"
                python_bin="$py"
                break
            fi
        fi
    done
    if [[ -z "$python_bin" ]]; then
        err "Python 3.10+ no encontrado"
        err "  Instalar: sudo apt install python3"
        all_ok=false
    fi

    # PyGObject / gi
    if [[ -n "$python_bin" ]]; then
        if "$python_bin" -c "import gi" &>/dev/null; then
            ok "PyGObject (gi)"
        else
            err "PyGObject no encontrado"
            err "  Instalar: sudo apt install python3-gi python3-gi-cairo"
            all_ok=false
        fi
    fi

    # GTK 4
    if [[ -n "$python_bin" ]]; then
        if "$python_bin" -c "import gi; gi.require_version('Gtk','4.0'); from gi.repository import Gtk" &>/dev/null 2>&1; then
            ok "GTK 4"
        else
            err "GTK 4 typelib no encontrado"
            err "  Instalar: sudo apt install gir1.2-gtk-4.0"
            all_ok=false
        fi
    fi

    # WebKit 6
    if [[ -n "$python_bin" ]]; then
        if "$python_bin" -c "import gi; gi.require_version('WebKit','6.0'); from gi.repository import WebKit" &>/dev/null 2>&1; then
            ok "WebKit 6.0"
        else
            err "WebKit 6.0 typelib no encontrado"
            err "  Instalar: sudo apt install gir1.2-webkit2-6.0"
            err "  (En sistemas más nuevos: sudo apt install gir1.2-webkitgtk-6.0)"
            all_ok=false
        fi
    fi

    # gtk-update-icon-cache
    if command -v gtk-update-icon-cache &>/dev/null; then
        ok "gtk-update-icon-cache"
    else
        warn "gtk-update-icon-cache no encontrado (opcional)"
        warn "  Instalar: sudo apt install libgtk-4-bin"
    fi

    # Extensión appindicator (solo informativa)
    if gnome-extensions info appindicatorsupport@rgcjonas.gmail.com &>/dev/null 2>&1; then
        local state
        state=$(gnome-extensions info appindicatorsupport@rgcjonas.gmail.com 2>/dev/null | grep "State:" | awk '{print $2}')
        if [[ "$state" == "ACTIVE" ]]; then
            ok "Extensión appindicatorsupport (tray) — ACTIVE"
        else
            warn "Extensión appindicatorsupport instalada pero no activa (estado: $state)"
            warn "  Activar: gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com"
        fi
    else
        warn "Extensión appindicatorsupport no instalada"
        warn "  Sin ella el icono del tray no se mostrará en GNOME Shell"
        warn "  Instalar desde: https://extensions.gnome.org/extension/615/"
        warn "  O: sudo apt install gnome-shell-extension-appindicator"
    fi

    echo ""
    if [[ "$all_ok" == "true" ]]; then
        ok "Todas las dependencias están disponibles"
        return 0
    else
        err "Faltan dependencias obligatorias"
        return 1
    fi
}

# ── Función: instalar ─────────────────────────────────────────
do_install() {
    echo ""
    echo -e "${BOLD}Instalando WhatsApp Desk...${NC}"
    echo "──────────────────────────────────────────"

    # Detectar Python
    local python_bin=""
    for py in python3 python3.12 python3.11 python3.10; do
        if command -v "$py" &>/dev/null; then
            if "$py" -c "import gi" &>/dev/null 2>&1; then
                python_bin="$py"
                break
            fi
        fi
    done
    [[ -z "$python_bin" ]] && die "No se encontró Python con PyGObject. Ejecuta: ./install.sh --check"

    # 1. Crear directorios
    mkdir -p "$APPS_DIR" "$ICON_DIR" "$BIN_DIR"
    ok "Directorios creados"

    # 2. Instalar iconos
    cp "$ICON_SRC" "$ICON_DST"
    cp "$ICON_SYM_SRC" "$ICON_SYM_DST"
    ok "Iconos instalados en $ICON_DIR"

    # 3. Actualizar caché de iconos
    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -t -f "$XDG_DATA_HOME/icons/hicolor/" 2>/dev/null && \
            ok "Caché de iconos GTK actualizada" || \
            warn "No se pudo actualizar la caché de iconos (no es crítico)"
    fi

    # 4. Instalar .desktop con la ruta del proyecto embebida
    # Sustituye el Exec= para que use el wrapper que crearemos
    sed "s|^Exec=.*|Exec=$WRAPPER_DST %U|" "$DESKTOP_SRC" > "$DESKTOP_DST"
    ok "Archivo .desktop instalado en $APPS_DIR"

    # 5. Actualizar base de datos de aplicaciones
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$APPS_DIR" 2>/dev/null && \
            ok "Base de datos de .desktop actualizada" || \
            warn "No se pudo actualizar la base de datos de .desktop"
    fi

    # 6. Crear wrapper de lanzamiento con PYTHONPATH
    cat > "$WRAPPER_DST" << WRAPPER_EOF
#!/usr/bin/env bash
# WhatsApp Desk — wrapper de lanzamiento (generado por install.sh)
# Proyecto: $PROJECT_DIR
PYTHONPATH="$PROJECT_DIR" exec $python_bin -m whatsapp_desk "\$@"
WRAPPER_EOF
    chmod +x "$WRAPPER_DST"
    ok "Wrapper creado en $WRAPPER_DST"

    # ── Resumen ───────────────────────────────────────────────
    echo ""
    echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║   WhatsApp Desk instalado correctamente  ║${NC}"
    echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Ejecutar:  whatsapp-desk"
    echo "  Lanzador:  busca 'WhatsApp Desk' en el menú de GNOME"
    echo ""

    # Aviso si ~/.local/bin no está en PATH
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        warn "~/.local/bin no está en tu PATH actual."
        warn "Añade esta línea a tu ~/.bashrc o ~/.profile:"
        warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        warn "Luego ejecuta: source ~/.bashrc"
    fi
}

# ── Main ─────────────────────────────────────────────────────
main() {
    echo -e "${BOLD}WhatsApp Desk — Instalador${NC}"

    case "${1:-}" in
        --check|-c)
            check_deps
            ;;
        --help|-h)
            echo "Uso: $0 [--check | --help]"
            echo "  (sin argumentos)  Instalar la aplicación"
            echo "  --check           Verificar dependencias del sistema"
            echo "  --help            Mostrar esta ayuda"
            ;;
        "")
            check_deps || die "Resuelve las dependencias antes de instalar."
            do_install
            ;;
        *)
            die "Argumento desconocido: $1. Usa --help para ver las opciones."
            ;;
    esac
}

main "$@"
