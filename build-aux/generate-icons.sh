#!/usr/bin/env bash
# Genera los iconos complementarios dentro del sandbox Flatpak.
# El icono unread se extrae del SVG inline definido en status_notifier.py.
set -euo pipefail

ICON_DIR="/app/share/icons/hicolor/scalable/apps"

python3 -c "
import ast, sys
with open('whatsapp_desk/status_notifier.py') as f:
    tree = ast.parse(f.read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == '_ICON_UNREAD_SVG':
            svg = node.value.value
            path = '$ICON_DIR/com.vladzur.WhatsAppDesk-unread-symbolic.svg'
            with open(path, 'w') as f:
                f.write(svg)
            print(f'Icono unread generado: {path}')
            sys.exit(0)
print('ERROR: No se encontró _ICON_UNREAD_SVG en status_notifier.py', file=sys.stderr)
sys.exit(1)
"
