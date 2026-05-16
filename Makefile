# WhatsApp Desk — Makefile
# ─────────────────────────────────────────────────────────────
# Targets:
#   make install    → instala la app para el usuario actual
#   make uninstall  → desinstala
#   make check      → verifica dependencias del sistema
#   make run        → lanza la app directamente desde el proyecto
#   make test       → ejecuta la suite de tests
#   make clean      → elimina __pycache__ y archivos temporales

.PHONY: install uninstall check run test clean help

# Python a usar (prioriza el que tenga PyGObject)
PYTHON := $(shell \
    for py in python3 python3.12 python3.11 python3.10; do \
        if command -v $$py >/dev/null 2>&1 && $$py -c "import gi" >/dev/null 2>&1; then \
            echo $$py; break; \
        fi; \
    done \
)

help:
	@echo "WhatsApp Desk — comandos disponibles:"
	@echo ""
	@echo "  make install    Instalar la aplicación (iconos, .desktop, wrapper)"
	@echo "  make uninstall  Desinstalar"
	@echo "  make check      Verificar dependencias del sistema"
	@echo "  make run        Lanzar directamente desde el proyecto"
	@echo "  make test       Ejecutar tests"
	@echo "  make clean      Limpiar archivos temporales"
	@echo ""

install:
	@bash install.sh

uninstall:
	@bash uninstall.sh

check:
	@bash install.sh --check

run:
	@if [ -z "$(PYTHON)" ]; then \
		echo "ERROR: No se encontró Python 3.10+ con PyGObject."; \
		echo "       Ejecuta: make check"; \
		exit 1; \
	fi
	@PYTHONPATH="$(CURDIR)" $(PYTHON) -m whatsapp_desk

test:
	@if [ -z "$(PYTHON)" ]; then \
		echo "ERROR: No se encontró Python 3.10+ con PyGObject."; \
		exit 1; \
	fi
	@PYTHONPATH="$(CURDIR)" $(PYTHON) -m pytest tests/ -v 2>/dev/null || \
	 PYTHONPATH="$(CURDIR)" $(PYTHON) tests/run_tests.py

clean:
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Limpieza completada."
