#!/usr/bin/env bash
# ============================================================
# WhatsApp Desk — Script de empaquetado Flatpak
# ============================================================
# Construye la aplicación como Flatpak y genera un bundle
# portable (.flatpak) para distribuir a otros equipos.
#
# Uso:
#   ./build-aux/build.sh
#
# Requisitos:
#   - flatpak >= 1.14
#   - flatpak-builder
#   - Runtime GNOME 47 (se instala automáticamente si no está)
# ============================================================

set -euo pipefail

APP_ID="com.vladzur.WhatsAppDesk"
BUILD_DIR=".flatpak-build"
OUTPUT="whatsapp-desk.flatpak"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "==> Verificando runtime GNOME 47..."
flatpak list --runtime 2>/dev/null | grep -q "org.gnome.Platform.*47" || {
    echo "    Instalando runtime GNOME 47 (esto puede tomar unos minutos)..."
    flatpak install --user -y flathub org.gnome.Platform/x86_64/47 org.gnome.Sdk/x86_64/47
}

cd "$PROJECT_DIR"

echo "==> Construyendo Flatpak..."
flatpak-builder --force-clean --user --install \
    "$BUILD_DIR" \
    build-aux/"$APP_ID".json

echo "==> Exportando al repositorio local..."
flatpak build-export \
    ~/.local/share/flatpak/repo \
    "$BUILD_DIR" \
    master

echo "==> Creando bundle portable..."
flatpak build-bundle \
    ~/.local/share/flatpak/repo \
    "$OUTPUT" \
    "$APP_ID" \
    master

echo ""
echo "============================================"
echo "  Bundle creado: $OUTPUT"
echo ""
echo "  Para instalar en otro PC:"
echo "    flatpak install --user $OUTPUT"
echo ""
echo "  Para ejecutar:"
echo "    flatpak run $APP_ID"
echo "============================================"
