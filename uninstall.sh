#!/usr/bin/env bash
# ============================================================
# WhatsApp Desk — Script de desinstalación
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✔${NC}  $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
ICON_DIR="$XDG_DATA_HOME/icons/hicolor/scalable/apps"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$XDG_DATA_HOME/applications"

echo -e "${BOLD}WhatsApp Desk — Desinstalador${NC}"
echo "──────────────────────────────────────────"

remove() {
    local f="$1"
    if [[ -f "$f" ]]; then
        rm -f "$f"
        ok "Eliminado: $f"
    else
        warn "No encontrado (ya eliminado?): $f"
    fi
}

remove "$APPS_DIR/whatsapp-desk.desktop"
remove "$ICON_DIR/whatsapp-desk.svg"
remove "$ICON_DIR/whatsapp-desk-symbolic.svg"
remove "$BIN_DIR/whatsapp-desk"

# Actualizar caches
command -v update-desktop-database &>/dev/null && \
    update-desktop-database "$APPS_DIR" 2>/dev/null && ok "Base de datos de .desktop actualizada"

command -v gtk-update-icon-cache &>/dev/null && \
    gtk-update-icon-cache -t -f "$XDG_DATA_HOME/icons/hicolor/" 2>/dev/null && ok "Caché de iconos actualizada"

echo ""
ok "WhatsApp Desk desinstalado. Los datos de usuario en ~/.local/share/whatsapp-desk y ~/.config/whatsapp-desk no se eliminaron."
echo "  Para eliminar también los datos: rm -rf ~/.local/share/whatsapp-desk ~/.config/whatsapp-desk"
