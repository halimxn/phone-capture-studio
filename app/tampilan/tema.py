"""Tema dan token desain Adobe Spectrum Dark tingkat lanjut untuk Phone Capture Studio.

Menerapkan prinsip clean design: hirarki tonal permukaan halus, hairline divider minimalis,
tiada border berdempet atau berlapis yang tidak perlu, dan tipografi kontras tinggi.
"""
import os


def aset(nama):
    """Jalur absolut aset untuk referensi image di QSS."""
    folder = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "aset"))
    return os.path.join(folder, nama).replace("\\", "/")


TOKEN = {
    # Permukaan Tonal Halus (Elevasi Berjenjang)
    "latar-kanvas": "#121212",          # Pasteboard kanvas paling dalam
    "latar-jendela": "#181818",         # Jendela luar
    "latar-panel": "#1e1e1e",           # Bilah alat & panel samping dock
    "latar-bar": "#181818",             # Bilah atas & status
    "latar-opsi": "#161616",            # Bilah opsi kontekstual
    "latar-input": "#222222",           # Kotak isian & display data
    "latar-hover": "rgba(255, 255, 255, 0.07)",
    "latar-tekan": "rgba(255, 255, 255, 0.12)",

    # Pembatas Halus (Minimal Hairline Dividers)
    "garis": "rgba(255, 255, 255, 0.07)",          # Garis pemisah struktural 1px
    "garis-terang": "rgba(255, 255, 255, 0.14)",   # Garis interaktif / hover
    "garis-lembut": "rgba(255, 255, 255, 0.04)",   # Garis sangat halus
    "garis-fokus": "#1473e6",                      # Biru fokus keyboard / aktif

    # Tipografi Adobe Spectrum
    "teks-utama": "#f2f2f2",            # Teks primer kontras tinggi
    "teks-kedua": "#ababab",            # Teks sekunder
    "teks-redup": "#8c8c8c",            # Keterangan / satuan / shortcut
    "teks-mati": "#5f5f5f",             # Teks tidak aktif / disabled

    # Aksen Biru Adobe Spectrum
    "aksen": "#1473e6",
    "aksen-atas": "#2680eb",
    "aksen-bawah": "#0e61d6",
    "aksen-hover-atas": "#3a8ff5",
    "aksen-hover-bawah": "#1471e8",
    "aksen-tekan": "#0953bc",
    "aksen-lembut": "rgba(20, 115, 230, 0.16)",
    "on-aksen": "#ffffff",

    # Status LED
    "status-ok": "#268e6c",             # Hijau Emerald
    "status-warn": "#e68619",           # Oranye Amber
    "status-err": "#d7373f",            # Merah Ruby
}


def qss_utama():
    """Lembar gaya QSS modern dengan estetika clean design murni tanpa border bertumpuk."""
    return f"""
    /* Reset & Tipografi Global */
    QWidget {{
        color: {TOKEN['teks-utama']};
        font-family: "Roboto", "Segoe UI", -apple-system, sans-serif;
        font-size: 12px;
        outline: none;
    }}

    QMainWindow, QDialog {{
        background-color: {TOKEN['latar-jendela']};
    }}

    /* Scrollbar Minimalis Ramping */
    QScrollBar:vertical {{
        background: transparent;
        width: 7px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(255, 255, 255, 0.28);
        min-height: 28px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(255, 255, 255, 0.45);
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 7px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: rgba(255, 255, 255, 0.28);
        min-width: 28px;
        border-radius: 3px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: rgba(255, 255, 255, 0.45);
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* Tombol Netral Standar (Subtle & Fluid) */
    QPushButton {{
        background-color: rgba(255, 255, 255, 0.05);
        color: {TOKEN['teks-utama']};
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 6px;
        padding: 5px 12px;
        font-weight: 500;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 0.09);
        border-color: rgba(255, 255, 255, 0.16);
        color: #ffffff;
    }}
    QPushButton:pressed {{
        background-color: rgba(255, 255, 255, 0.03);
        border-color: rgba(255, 255, 255, 0.06);
        padding-top: 6px;
        padding-bottom: 4px;
    }}
    QPushButton:disabled {{
        background-color: rgba(255, 255, 255, 0.02);
        color: {TOKEN['teks-mati']};
        border-color: transparent;
    }}
    QPushButton:focus {{
        border-color: {TOKEN['garis-fokus']};
    }}

    /* Tombol Utama (Hero CTA Blue) */
    QPushButton.primer {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {TOKEN['aksen-atas']}, stop:1 {TOKEN['aksen-bawah']});
        color: #ffffff;
        border: 1px solid {TOKEN['aksen']};
        border-top: 1px solid rgba(255, 255, 255, 0.35);
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton.primer:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {TOKEN['aksen-hover-atas']}, stop:1 {TOKEN['aksen-hover-bawah']});
        border-color: #2482ff;
    }}
    QPushButton.primer:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0d54b8, stop:1 #094396);
        border-color: #07387d;
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    QPushButton.primer:disabled {{
        background: #172c44;
        color: #4f6e8f;
        border: 1px solid #1a334f;
    }}

    /* Tombol Sekunder Ringkas */
    QPushButton.halus {{
        background: rgba(255, 255, 255, 0.04);
        color: {TOKEN['teks-kedua']};
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 5px;
        padding: 4px 10px;
        font-size: 11px;
        font-weight: 500;
    }}
    QPushButton.halus:hover {{
        background: rgba(255, 255, 255, 0.09);
        border-color: rgba(255, 255, 255, 0.16);
        color: #ffffff;
    }}
    QPushButton.halus:pressed {{
        background: rgba(255, 255, 255, 0.03);
    }}
    QPushButton.halus:disabled {{
        background: transparent;
        color: {TOKEN['teks-mati']};
        border-color: transparent;
    }}
    QPushButton.halus:focus {{
        border-color: {TOKEN['garis-fokus']};
        color: #ffffff;
    }}

    /* Dropdown / ComboBox Bersih */
    QComboBox {{
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 6px;
        padding: 4px 10px;
        color: {TOKEN['teks-utama']};
        font-size: 12px;
        min-height: 22px;
    }}
    QComboBox:hover {{
        background: rgba(255, 255, 255, 0.07);
        border-color: rgba(255, 255, 255, 0.16);
    }}
    QComboBox:focus {{
        border-color: {TOKEN['aksen']};
    }}
    QComboBox:disabled {{
        background: rgba(255, 255, 255, 0.02);
        color: {TOKEN['teks-mati']};
        border-color: transparent;
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: none;
    }}
    QComboBox::down-arrow {{
        image: url("{aset('chevron.svg')}");
        width: 10px;
        height: 10px;
    }}
    QComboBox QAbstractItemView {{
        background-color: #202020;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 6px;
        selection-background-color: {TOKEN['aksen']};
        selection-color: #ffffff;
        outline: none;
        padding: 4px;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 26px;
        padding: 2px 8px;
    }}

    /* Checkbox Elegan */
    QCheckBox {{
        spacing: 8px;
        color: {TOKEN['teks-utama']};
        font-size: 12px;
    }}
    QCheckBox:disabled {{
        color: {TOKEN['teks-mati']};
    }}
    QCheckBox::indicator {{
        width: 15px;
        height: 15px;
        border: 1px solid rgba(255, 255, 255, 0.20);
        border-radius: 4px;
        background-color: rgba(255, 255, 255, 0.04);
    }}
    QCheckBox::indicator:hover {{
        border-color: {TOKEN['aksen']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {TOKEN['aksen']};
        border-color: {TOKEN['aksen']};
        image: url("{aset('centang.svg')}");
    }}
    QCheckBox::indicator:checked:hover {{
        border-color: #3a8ff5;
        background-color: #3a8ff5;
    }}
    QCheckBox:focus::indicator {{
        border-color: {TOKEN['garis-fokus']};
    }}
    QCheckBox::indicator:disabled {{
        background-color: rgba(255, 255, 255, 0.03);
        border-color: rgba(255, 255, 255, 0.08);
    }}

    /* List Widget Riwayat Tanpa Border Bertumpuk */
    QListWidget {{
        background-color: transparent;
        border: none;
        padding: 0px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 6px 8px;
        border-radius: 6px;
        color: {TOKEN['teks-utama']};
        margin-bottom: 3px;
        border: none;
    }}
    QListWidget::item:hover {{
        background-color: rgba(255, 255, 255, 0.05);
    }}
    QListWidget::item:selected {{
        background-color: {TOKEN['aksen-lembut']};
        color: #ffffff;
    }}

    /* Tooltip Minimalis */
    QToolTip {{
        background-color: #181818;
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 11px;
    }}

    /* Splitter Hairline */
    QSplitter::handle {{
        background-color: {TOKEN['garis']};
    }}
    QSplitter::handle:hover {{
        background-color: {TOKEN['aksen']};
    }}
    """
