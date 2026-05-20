"""Gestor de descargas para WhatsApp Desk.

Intercepta las descargas iniciadas por WebKit, muestra un diálogo
nativo de GTK para elegir el destino y reporta el progreso en la
barra de título de la ventana.
"""

import os
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import GLib, Gtk, WebKit  # noqa: E402


# Carpeta de descargas predeterminada (XDG)
DEFAULT_DOWNLOAD_DIR = GLib.get_user_special_dir(
    GLib.UserDirectory.DIRECTORY_DOWNLOAD
) or os.path.expanduser("~/Descargas")


class DownloadManager:
    """Gestiona las descargas iniciadas desde el WebView de WhatsApp.

    Se conecta a la señal `download-started` de la NetworkSession
    para interceptar cada descarga y mostrar un diálogo de guardado.
    """

    def __init__(self, network_session: WebKit.NetworkSession, window: Gtk.Window):
        self._window = window
        self._active_downloads: dict[WebKit.Download, str] = {}
        network_session.connect("download-started", self._on_download_started)

    # ── Señales de NetworkSession ─────────────────────────────────────────

    def _on_download_started(
        self, session: WebKit.NetworkSession, download: WebKit.Download
    ):
        """Llamado cuando WebKit inicia una descarga."""
        # decide-destination se emite antes de que comience la transferencia
        download.connect("decide-destination", self._on_decide_destination)
        download.connect("finished", self._on_download_finished)
        download.connect("failed", self._on_download_failed)
        download.connect("notify::estimated-progress", self._on_progress_changed)

    # ── Señales de WebKit.Download ────────────────────────────────────────

    def _on_decide_destination(
        self, download: WebKit.Download, suggested_filename: str
    ) -> bool:
        """Muestra un diálogo para elegir dónde guardar el archivo.

        Devuelve True para indicar a WebKit que hemos manejado el destino.
        """
        dialog = Gtk.FileDialog()
        dialog.set_title("Guardar archivo")
        dialog.set_initial_name(suggested_filename or "descarga")
        dialog.set_initial_folder(
            Gio_file_for_path(DEFAULT_DOWNLOAD_DIR)
        )

        # Abrir el diálogo de forma asíncrona para no bloquear el hilo principal
        dialog.save(self._window, None, self._on_save_dialog_response, download)
        return True  # Indicamos a WebKit que manejaremos el destino

    def _on_save_dialog_response(self, dialog, result, download: WebKit.Download):
        """Callback del diálogo de guardado."""
        try:
            gfile = dialog.save_finish(result)
            path = gfile.get_path()
            download.set_destination(path)
            self._active_downloads[download] = path
            self._update_title(download)
        except GLib.Error:
            # El usuario canceló el diálogo — cancelar la descarga
            download.cancel()

    def _on_progress_changed(self, download: WebKit.Download, _param):
        """Actualiza el título con el progreso de la descarga."""
        self._update_title(download)

    def _on_download_finished(self, download: WebKit.Download):
        """Muestra una notificación al terminar la descarga."""
        path = self._active_downloads.pop(download, None)
        filename = os.path.basename(path) if path else "Archivo"
        self._restore_title()
        self._notify_finished(filename, path)

    def _on_download_failed(self, download: WebKit.Download, error: GLib.Error):
        """Muestra una alerta de error si la descarga falla."""
        self._active_downloads.pop(download, None)
        self._restore_title()
        if error and error.code != 400:  # 400 = cancelado por el usuario
            alert = Gtk.AlertDialog()
            alert.set_message("Error al descargar")
            alert.set_detail(f"No se pudo completar la descarga:\n{error.message}")
            alert.set_buttons(["Aceptar"])
            alert.show(self._window)

    # ── Helpers de UI ─────────────────────────────────────────────────────

    def _update_title(self, download: WebKit.Download):
        """Actualiza el título de la ventana con el progreso."""
        progress = download.get_estimated_progress()
        path = self._active_downloads.get(download)
        filename = os.path.basename(path) if path else "Descargando…"
        pct = int(progress * 100)
        self._window.set_title(f"WhatsApp Desk — {filename} ({pct}%)")

    def _restore_title(self):
        """Restaura el título original de la ventana."""
        if not self._active_downloads:
            self._window.set_title("WhatsApp Desk")

    def _notify_finished(self, filename: str, path: str | None):
        """Muestra un diálogo de éxito al completar la descarga."""
        alert = Gtk.AlertDialog()
        alert.set_message("Descarga completada")
        detail = f"'{filename}' se guardó correctamente."
        if path:
            detail += f"\n{path}"
        alert.set_detail(detail)
        alert.set_buttons(["Aceptar"])
        alert.show(self._window)


def Gio_file_for_path(path: str):
    """Helper para crear un Gio.File desde una ruta."""
    from gi.repository import Gio
    return Gio.File.new_for_path(path)
