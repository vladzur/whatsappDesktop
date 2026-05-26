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
#   - Runtime GNOME 49 (se instala automáticamente si no está)
# ============================================================

set -euo pipefail

APP_ID="com.vladzur.WhatsAppDesk"
BUILD_DIR=".flatpak-build"
OUTPUT="whatsapp-desk.flatpak"
BRANCH="stable"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Detectar versión desde el último git tag (ej: v1.0.6 → 1.0.6)
VERSION="$(git -C "$PROJECT_DIR" describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo '0.0.0-dev')"
echo "==> Versión detectada: $VERSION"

echo "==> Verificando runtime GNOME 49..."
flatpak list --runtime 2>/dev/null | grep -q "org.gnome.Platform.*49" || {
    echo "    Instalando runtime GNOME 49 (esto puede tomar unos minutos)..."
    flatpak install --user -y flathub org.gnome.Platform/x86_64/49 org.gnome.Sdk/x86_64/49
}

cd "$PROJECT_DIR"

# Inyectar versión en metainfo (in-place, se restaura tras el build)
echo "==> Inyectando versión $VERSION en metainfo..."
sed -i "s/@VERSION@/$VERSION/" "$APP_ID.metainfo.xml"

# Generar manifiesto temporal con la versión inyectada
echo "==> Generando manifiesto con versión $VERSION..."
jq --arg version "$VERSION" \
    '.modules[0]."build-options".env.WHATSAPP_DESK_VERSION = $version' \
    build-aux/"$APP_ID".json > build-aux/.local-manifest.json

echo "==> Construyendo Flatpak..."
flatpak-builder --force-clean --user \
    "$BUILD_DIR" \
    build-aux/.local-manifest.json

# Restaurar archivos temporales
rm -f build-aux/.local-manifest.json
git checkout -- "$APP_ID.metainfo.xml" 2>/dev/null || true

echo "==> Exportando al repositorio local..."
flatpak build-export \
    ~/.local/share/flatpak/repo \
    "$BUILD_DIR" \
    "$BRANCH"

echo "==> Creando bundle portable..."
flatpak build-bundle \
    ~/.local/share/flatpak/repo \
    "$OUTPUT" \
    "$APP_ID" \
    "$BRANCH"

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
