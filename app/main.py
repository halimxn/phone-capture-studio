"""Titik masuk utama aplikasi Phone Capture Studio dengan dukungan High-DPI dan tema Fusion."""
import multiprocessing
import os
import sys

DIR_APP = os.path.dirname(os.path.abspath(__file__))
if DIR_APP not in sys.path:
    sys.path.insert(0, DIR_APP)

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from tampilan import tema
from tampilan.jendela import JendelaUtama

NAMA_SOKET = "PhoneCaptureStudio.Satu"


def sudah_berjalan():
    """Mencegah multi-instance; jika sudah berjalan, fokuskan jendela yang ada."""
    s = QLocalSocket()
    s.connectToServer(NAMA_SOKET)
    if s.waitForConnected(300):
        s.write(b"fokus")
        s.flush()
        s.waitForBytesWritten(300)
        s.disconnectFromServer()
        return True
    return False


def pasang_server_satu_contoh(jendela):
    QLocalServer.removeServer(NAMA_SOKET)
    server = QLocalServer(jendela)
    server.listen(NAMA_SOKET)

    def tangani():
        s = server.nextPendingConnection()
        if s:
            s.readAll()
            jendela.setWindowState(jendela.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
            jendela.showMaximized()
            jendela.raise_()
            jendela.activateWindow()

    server.newConnection.connect(tangani)
    return server


def main():
    multiprocessing.freeze_support()

    if sudah_berjalan():
        sys.exit(0)

    # Kebijakan High-DPI untuk ketajaman tampilan pada layar resolusi tinggi (125%, 150%, 200%)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("Phone Capture Studio")
    app.setOrganizationName("Halim")

    # Gunakan dasar Fusion agar tema gelap QSS diterapkan konsisten tanpa override gaya WindowsVista
    app.setStyle("Fusion")

    # Muat Tema Adobe Spectrum
    app.setStyleSheet(tema.qss_utama())

    # Pasang Ikon Aplikasi
    icon_path = os.path.join(DIR_APP, "aset", "ikon.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Pasang Font Roboto bawaan aplikasi dengan petunjuk anti-aliasing
    from PySide6.QtGui import QFontDatabase
    font_path = os.path.join(DIR_APP, "aset", "Roboto.ttf")
    if os.path.isfile(font_path):
        QFontDatabase.addApplicationFont(font_path)
        font = QFont("Roboto")
    else:
        font = QFont("Segoe UI", 9)
    font.setPixelSize(12)
    font.setStyleStrategy(QFont.PreferAntialias)
    font.setHintingPreference(QFont.PreferNoHinting)
    app.setFont(font)

    jendela = JendelaUtama()
    server = pasang_server_satu_contoh(jendela)

    jendela.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
