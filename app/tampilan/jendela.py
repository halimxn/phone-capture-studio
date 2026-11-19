"""Jendela utama Phone Capture Studio: UI/UX profesional Adobe Spectrum dengan QSplitter & QThread."""
import io
import math
import os
import subprocess
from PIL import Image
from PySide6.QtCore import QSettings, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from engine import adb, lokasi, processor
from . import komponen, tema
from .kanvas import KanvasAdobe


def _pemisah():
    """Garis pemisah tipis untuk mengelompokkan kontrol dalam satu bilah."""
    garis = QFrame()
    garis.setFixedSize(1, 16)
    garis.setStyleSheet(f"background: {tema.TOKEN['garis-terang']}; border: none;")
    return garis


EKSTENSI_GAMBAR = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def _baca_status_hp():
    """Dijalankan di benang latar: semua panggilan adb yang lambat dikumpulkan di sini."""
    serial, status, pesan = adb.cek_perangkat()
    model = info = None
    if status == "device":
        model = adb.model_perangkat(serial) or "Perangkat Android"
        info = adb.info_layar(serial)
    return serial, status, model, info


def _potong_massal(folder, folder_asli, lapor):
    """Memotong layar penampil di folder; yang sudah dipotong dilewati, aslinya dicadangkan."""
    import shutil
    berkas = sorted(f for f in os.listdir(folder) if f.lower().endswith(".png"))
    dipotong = dilewati = gagal = 0
    for i, f in enumerate(berkas, 1):
        lapor(i, len(berkas))
        jalur = os.path.join(folder, f)
        try:
            with Image.open(jalur) as img:
                img.load()
                if not processor.belum_dipotong(img):
                    dilewati += 1
                    continue
                x, y, w, h = processor.deteksi_kotak_foto(img)
                if w <= 100 or h <= 100:
                    dilewati += 1
                    continue
                cadangan = os.path.join(folder_asli, f)
                if not os.path.exists(cadangan):
                    shutil.copy2(jalur, cadangan)
                potongan = img.crop((x, y, x + w, y + h))
            potongan.save(jalur, optimize=True)
            dipotong += 1
        except Exception:
            gagal += 1
    return {"dipotong": dipotong, "dilewati": dilewati, "gagal": gagal, "total": len(berkas)}


def _hd_massal(folder, folder_hd, lapor):
    berkas = sorted(f for f in os.listdir(folder) if f.lower().endswith(".png"))
    dibuat = gagal = 0
    for i, f in enumerate(berkas, 1):
        lapor(i, len(berkas))
        try:
            with Image.open(os.path.join(folder, f)) as img:
                hd = processor.proses_hd_lanczos(img)
            hd.save(os.path.join(folder_hd, f.replace("layar_", "hd_")), optimize=True)
            dibuat += 1
        except Exception:
            gagal += 1
    return {"dibuat": dibuat, "gagal": gagal, "total": len(berkas)}


class PekerjaFungsi(QThread):
    """Menjalankan fungsi biasa di benang latar. Hasil: (hasil, galat)."""

    selesai = Signal(object, object)
    kemajuan = Signal(int, int)

    def __init__(self, fn, *args, dengan_kemajuan=False):
        super().__init__()
        self.fn = fn
        self.args = args
        self.dengan_kemajuan = dengan_kemajuan

    def run(self):
        try:
            if self.dengan_kemajuan:
                hasil = self.fn(*self.args, self.kemajuan.emit)
            else:
                hasil = self.fn(*self.args)
            self.selesai.emit(hasil, None)
        except Exception as e:
            self.selesai.emit(None, str(e))


class PekerjaAmbilLayar(QThread):
    """Benang latar belakang untuk mengambil tangkapan layar via ADB tanpa memblokir antarmuka."""

    selesai = Signal(object, str)

    def run(self):
        # Status diperiksa di sini (bukan di benang UI) agar F5 tidak membuat jendela tersendat
        serial, status, pesan = adb.cek_perangkat()
        if status != "device":
            self.selesai.emit(None, pesan)
            return
        raw_png, err = adb.ambil_tangkapan_layar(serial)
        self.selesai.emit(raw_png, err)


class PekerjaSimpan(QThread):
    """Benang latar belakang untuk memotong, menyimpan, dan upscaling 2x Lanczos."""

    selesai = Signal(object, str)

    def __init__(self, img_pil, crop_box, buat_hd=False, simpan_raw=False):
        super().__init__()
        self.img_pil = img_pil
        self.box = crop_box
        self.buat_hd = buat_hd
        self.simpan_raw = simpan_raw

    def run(self):
        try:
            x, y, w, h = self.box
            crop_img = processor.potong_koordinat(self.img_pil, x, y, w, h)
            if not crop_img:
                self.selesai.emit(None, "Ukuran seleksi terlalu kecil")
                return

            hasil = processor.simpan_hasil(crop_img, buat_hd=self.buat_hd)

            if self.simpan_raw:
                processor.simpan_layar_penuh(self.img_pil)

            self.selesai.emit(hasil, None)
        except Exception as e:
            self.selesai.emit(None, str(e))


class JendelaUtama(QMainWindow):
    """Jendela utama aplikasi Phone Capture Studio."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phone Capture Studio")
        self.resize(1280, 860)
        self.setMinimumSize(960, 660)

        # Terapkan mode gelap pada bilah jendela Windows (DWM Immersive Dark Mode)
        self._terapkan_mode_gelap_windows()

        # State aplikasi
        self.serial_hp = None
        self.info_hp = None
        self.nama_model_hp = ""
        self.pil_layar_saat_ini = None
        self.pixmap_saat_ini = None
        self.sedang_mengambil = False
        self.sedang_menyimpan = False
        self.sedang_batch = False
        self._status_koneksi = None
        self._cek_berjalan = False
        self._total_foto = 0
        self._pekerja = set()
        self.setAcceptDrops(True)

        self._bangun_ui()
        self._pasang_pintasan()

        # Polling status koneksi berkala (non-blocking)
        self.timer_status = QTimer(self)
        self.timer_status.timeout.connect(self._perbarui_status_hp)
        self.timer_status.start(3500)

        QTimer.singleShot(150, self._perbarui_status_hp)
        self._muat_riwayat_awal()
        self._muat_pengaturan()
        self._perbarui_kontrol()
        self.kanvas_widget.kanvas.setFocus()

    def _terapkan_mode_gelap_windows(self):
        """Membuat bilah judul Windows 10/11 mengikuti tema gelap Adobe tanpa bilah putih menyilaukan."""
        try:
            import ctypes
            hwnd = int(self.winId())
            val = ctypes.c_int(1)
            for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass

    def showEvent(self, ev):
        super().showEvent(ev)
        self._terapkan_mode_gelap_windows()

    def _bangun_ui(self):
        wadah_utama = QWidget()
        self.setCentralWidget(wadah_utama)
        lay_induk = QVBoxLayout(wadah_utama)
        lay_induk.setContentsMargins(0, 0, 0, 0)
        lay_induk.setSpacing(0)

        # 1. Bilah Atas (Top App Bar)
        lay_induk.addWidget(self._buat_bilah_atas())

        # 2. Bilah Opsi Kontekstual (Options Bar)
        lay_induk.addWidget(self._buat_bilah_opsi())

        # 3. Area Kerja Tengah Responsif (Rel Alat + QSplitter Kanvas & Inspector)
        tengah = QWidget()
        lay_tengah = QHBoxLayout(tengah)
        lay_tengah.setContentsMargins(0, 0, 0, 0)
        lay_tengah.setSpacing(0)

        # Rel Alat Vertikal Kiri
        lay_tengah.addWidget(self._buat_rel_alat())

        # QSplitter Responsif: Kanvas (fleksibel) + Panel Samping (dock)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)

        # Kanvas Interaktif
        self.kanvas_widget = KanvasAdobe(self)
        self.kanvas_widget.kanvas.seleksi_berubah.connect(self._pada_seleksi_berubah)
        self.kanvas_widget.kanvas.zoom_berubah.connect(self._pada_zoom_berubah)
        self.kanvas_widget.kanvas.minta_ambil_layar.connect(self._aksi_ambil_layar)
        self.splitter.addWidget(self.kanvas_widget)

        # Panel Samping Kanan
        self.panel_kanan = self._buat_panel_kanan()
        self.splitter.addWidget(self.panel_kanan)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([960, 320])

        lay_tengah.addWidget(self.splitter, 1)
        lay_induk.addWidget(tengah, 1)

        # 4. Bilah Status Bawah (Status Bar)
        lay_induk.addWidget(self._buat_bilah_status())

        # 5. Notifikasi Mengambang (Floating Toast)
        self.toast = komponen.NotifikasiToast(self.kanvas_widget)

    def _buat_bilah_atas(self):
        bar = QFrame()
        bar.setFixedHeight(44)
        bar.setObjectName("bilahAtas")
        bar.setStyleSheet(f"""
            QFrame#bilahAtas {{
                background-color: {tema.TOKEN['latar-bar']};
                border: none;
                border-bottom: 1px solid {tema.TOKEN['garis']};
            }}
        """)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 10, 0)
        lay.setSpacing(4)

        # Logo Studio Adobe "Pc"
        mark = QLabel("Pc")
        mark.setFixedSize(26, 26)
        mark.setAlignment(Qt.AlignCenter)
        mark.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1473e6, stop:1 #0c57b8);
            color: #ffffff;
            font-weight: 800;
            font-size: 12px;
            border-radius: 5px;
        """)
        lay.addWidget(mark)
        lay.addSpacing(10)

        mark.setToolTip("Phone Capture Studio")

        # Indikator Layar Aktif (Clean & Borderless)
        self.tab_dokumen = QWidget()
        lay_tab = QHBoxLayout(self.tab_dokumen)
        lay_tab.setContentsMargins(0, 0, 0, 0)
        lay_tab.setSpacing(6)

        self.lbl_dokumen = QLabel("Belum ada layar")
        self.lbl_dokumen.setStyleSheet(f"color: {tema.TOKEN['teks-kedua']}; font-size: 12px;")
        lay_tab.addWidget(self.lbl_dokumen)

        lay.addWidget(self.tab_dokumen)
        lay.addStretch(1)

        # Lencana status HP interaktif
        self.lencana_hp = komponen.LencanaStatus("Memeriksa HP…", "warn")
        self.lencana_hp.setCursor(Qt.PointingHandCursor)
        self.lencana_hp.setToolTip("Klik untuk memperbarui status koneksi USB")
        self.lencana_hp.mousePressEvent = lambda _: self._perbarui_status_hp()
        lay.addWidget(self.lencana_hp)
        lay.addSpacing(6)
        lay.addWidget(_pemisah())
        lay.addSpacing(6)

        # Tombol pintas buka folder hasil (Clean Ghost Button)
        btn_buka = komponen.TombolChipAksi("Buka Gambar", jenis_ikon="gambar", tip="Buka tangkapan layar dari PC (Ctrl+O). Bisa juga diseret ke jendela.")
        btn_buka.clicked.connect(self._aksi_buka_berkas)
        lay.addWidget(btn_buka)

        btn_folder = komponen.TombolChipAksi("Folder Hasil", jenis_ikon="folder", tip="Buka folder penyimpanan foto di Windows Explorer")
        btn_folder.clicked.connect(lambda: os.startfile(lokasi.folder_hasil()))
        lay.addWidget(btn_folder)

        # Tombol toggle Layar Penuh (F11)
        self.btn_fullscreen = komponen.TombolChipAksi("Layar Penuh", jenis_ikon="layar_penuh", tip="Beralih ke mode layar penuh (F11)")
        self.btn_fullscreen.clicked.connect(self._toggle_layar_penuh)
        lay.addWidget(self.btn_fullscreen)

        # Tombol toggle panel samping
        self.btn_toggle_panel = komponen.TombolChipAksi(jenis_ikon="panel", tip="Sembunyikan / tampilkan panel kanan (Tab)")
        self.btn_toggle_panel.setFixedWidth(28)
        self.btn_toggle_panel.clicked.connect(self._toggle_panel_samping)
        lay.addWidget(self.btn_toggle_panel)

        return bar

    def _buat_bilah_opsi(self):
        bar = QFrame()
        bar.setObjectName("bilahOpsi")
        bar.setFixedHeight(42)
        bar.setStyleSheet(f"""
            QFrame#bilahOpsi {{
                background-color: {tema.TOKEN['latar-opsi']};
                border: none;
                border-bottom: 1px solid {tema.TOKEN['garis']};
            }}
        """)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(12)

        def label(teks):
            lbl = QLabel(teks)
            lbl.setStyleSheet(f"color: {tema.TOKEN['teks-redup']}; font-size: 12px;")
            return lbl

        def grup(*widget):
            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(8)
            for x in widget:
                l.addWidget(x, 0, Qt.AlignVCenter)
            return w

        self.box_dimensi = komponen.KotakDimensiTerpadu()
        lay.addWidget(self.box_dimensi, 0, Qt.AlignVCenter)
        lay.addWidget(_pemisah(), 0, Qt.AlignVCenter)

        self.cmb_rasio = QComboBox()
        self.cmb_rasio.setFixedSize(148, 26)
        self.cmb_rasio.addItems([
            "Bebas",
            "1:1 Persegi",
            "3:4 Pas Foto",
            "4:5 Portrait",
            "9:16 Layar",
            "16:9 Landscape",
        ])
        self.cmb_rasio.currentIndexChanged.connect(self._pada_pilihan_rasio)
        lay.addWidget(grup(label("Rasio"), self.cmb_rasio), 0, Qt.AlignVCenter)
        lay.addWidget(_pemisah(), 0, Qt.AlignVCenter)

        self.seg_zoom = komponen.SegmenPilihanAdobe(["Pas", "50%", "100%", "200%"], terpilih=0)
        self.seg_zoom.dipilih.connect(self._pada_pilihan_zoom)
        lay.addWidget(grup(label("Zoom"), self.seg_zoom), 0, Qt.AlignVCenter)

        lay.addStretch(1)

        self.btn_pilih_semua = QPushButton("Pilih Semua")
        self.btn_pilih_semua.setFixedHeight(26)
        self.btn_pilih_semua.setProperty("class", "halus")
        self.btn_pilih_semua.setToolTip("Pilih seluruh area layar (Ctrl+A)")
        self.btn_pilih_semua.clicked.connect(self._pilih_seluruh_layar)

        self.btn_hapus_seleksi = QPushButton("Hapus Seleksi")
        self.btn_hapus_seleksi.setFixedHeight(26)
        self.btn_hapus_seleksi.setProperty("class", "halus")
        self.btn_hapus_seleksi.setToolTip("Hapus kotak seleksi (Esc)")
        self.btn_hapus_seleksi.clicked.connect(self._batal_seleksi)
        lay.addWidget(grup(self.btn_pilih_semua, self.btn_hapus_seleksi), 0, Qt.AlignVCenter)

        return bar

    def _buat_rel_alat(self):
        rail = QFrame()
        rail.setFixedWidth(46)
        rail.setObjectName("relAlat")
        rail.setStyleSheet(f"""
            QFrame#relAlat {{
                background-color: {tema.TOKEN['latar-bar']};
                border: none;
                border-right: 1px solid {tema.TOKEN['garis']};
            }}
        """)
        lay = QVBoxLayout(rail)
        lay.setContentsMargins(5, 8, 5, 8)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignTop)

        self.tool_sel = komponen.TombolAlatAdobe("seleksi", "Seleksi Persegi (M)")
        self.tool_sel.setChecked(True)
        self.tool_sel.clicked.connect(lambda: self._ganti_alat("seleksi"))
        lay.addWidget(self.tool_sel)

        self.tool_pan = komponen.TombolAlatAdobe("geser", "Geser Kanvas (H / Klik Kanan)")
        self.tool_pan.clicked.connect(lambda: self._ganti_alat("geser"))
        lay.addWidget(self.tool_pan)

        self.tool_zoom = komponen.TombolAlatAdobe("zoom", "Perbesar Kanvas (Z)")
        self.tool_zoom.clicked.connect(lambda: self._ganti_alat("zoom"))
        lay.addWidget(self.tool_zoom)

        lay.addSpacing(6)

        garis = QFrame()
        garis.setFixedHeight(1)
        garis.setStyleSheet("background: rgba(255, 255, 255, 0.10); border: none;")
        lay.addWidget(garis)
        lay.addSpacing(2)

        self.tool_auto = komponen.TombolAlatAdobe("otomatis", "Pilih area foto otomatis (A)")
        self.tool_auto.clicked.connect(self._aksi_potong_otomatis)
        lay.addWidget(self.tool_auto)

        self.tool_cap = komponen.TombolAlatAdobe("kamera", "Ambil Layar HP (F5)")
        self.tool_cap.clicked.connect(self._aksi_ambil_layar)
        lay.addWidget(self.tool_cap)

        return rail

    def _buat_panel_kanan(self):
        scroll = QScrollArea()
        scroll.setMinimumWidth(300)
        scroll.setMaximumWidth(380)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {tema.TOKEN['latar-panel']};
                border: none;
                border-left: 1px solid {tema.TOKEN['garis']};
            }}
        """)

        konten = QWidget()
        konten.setStyleSheet(f"background-color: {tema.TOKEN['latar-panel']};")
        lay = QVBoxLayout(konten)
        lay.setContentsMargins(0, 0, 0, 16)
        lay.setSpacing(0)

        # 1. Panel Aksi Utama (Satu tombol utama yang mengikuti langkah berikutnya)
        p_ekspor = komponen.PanelAccordionAdobe("Aksi & Simpan", terbuka=True)
        self.btn_utama = komponen.TombolAksiHero("Ambil Layar HP", shortcut="F5", jenis_ikon="kamera")
        self.btn_utama.clicked.connect(self._aksi_utama)
        p_ekspor.tambah_widget(self.btn_utama)

        self.lbl_petunjuk = QLabel("Sambungkan ponsel via USB, lalu ambil layar.")
        self.lbl_petunjuk.setWordWrap(True)
        self.lbl_petunjuk.setStyleSheet(f"color: {tema.TOKEN['teks-redup']}; font-size: 11px;")
        p_ekspor.tambah_widget(self.lbl_petunjuk)

        self.btn_auto = komponen.TombolAksiTaktil("Pilih Area Otomatis", shortcut="A", jenis_ikon="otomatis")
        self.btn_auto.setToolTip("Deteksi batas foto pada layar secara otomatis")
        self.btn_auto.clicked.connect(self._aksi_potong_otomatis)
        self.btn_auto.setVisible(False)
        p_ekspor.tambah_widget(self.btn_auto)

        self.btn_salin = komponen.TombolAksiTaktil("Salin ke Clipboard", shortcut="Ctrl+C", jenis_ikon="salin")
        self.btn_salin.setToolTip("Salin area terpilih untuk ditempel di WhatsApp, Word, dan lainnya")
        self.btn_salin.clicked.connect(self._aksi_salin)
        self.btn_salin.setVisible(False)
        p_ekspor.tambah_widget(self.btn_salin)

        self.btn_ambil_layar = komponen.TombolAksiTaktil("Ambil Ulang Layar", shortcut="F5", jenis_ikon="kamera")
        self.btn_ambil_layar.clicked.connect(self._aksi_ambil_layar)
        self.btn_ambil_layar.setVisible(False)
        p_ekspor.tambah_widget(self.btn_ambil_layar)

        self.chk_hd = QCheckBox("Simpan versi HD 2x")
        self.chk_hd.setChecked(True)
        self.chk_hd.setToolTip("Hasil 2x lebih tajam dengan Lanczos tanpa mengubah bentuk wajah")
        p_ekspor.tambah_widget(self.chk_hd)

        self.chk_raw = QCheckBox("Simpan layar penuh sebagai cadangan")
        p_ekspor.tambah_widget(self.chk_raw)
        lay.addWidget(p_ekspor)

        # 2. Panel Perangkat (Info ringkas; kontrol HD hanya muncul saat HP terhubung)
        p_device = komponen.PanelAccordionAdobe("Perangkat", terbuka=True)
        self.box_hp_info = QWidget()
        lay_box = QVBoxLayout(self.box_hp_info)
        lay_box.setContentsMargins(0, 0, 0, 2)
        lay_box.setSpacing(4)

        self.lbl_info_model = QLabel("Tidak ada perangkat terdeteksi")
        self.lbl_info_model.setWordWrap(True)
        self.lbl_info_model.setStyleSheet(f"color: {tema.TOKEN['teks-utama']}; font-weight: 600; font-size: 12px;")
        lay_box.addWidget(self.lbl_info_model)

        self.lbl_info_res = QLabel("Resolusi: -")
        self.lbl_info_res.setStyleSheet(f"color: {tema.TOKEN['teks-kedua']}; font-size: 11px;")
        self.lbl_info_res.setVisible(False)
        lay_box.addWidget(self.lbl_info_res)

        self.lbl_info_dpi = QLabel("Kepadatan: -")
        self.lbl_info_dpi.setStyleSheet(f"color: {tema.TOKEN['teks-redup']}; font-size: 11px;")
        self.lbl_info_dpi.setVisible(False)
        lay_box.addWidget(self.lbl_info_dpi)

        p_device.tambah_widget(self.box_hp_info)

        self.grup_hd = QWidget()
        lay_hd = QVBoxLayout(self.grup_hd)
        lay_hd.setContentsMargins(0, 0, 0, 0)
        lay_hd.setSpacing(8)

        lbl_zoom_hp = QLabel("Skala render di HP")
        lbl_zoom_hp.setStyleSheet(f"color: {tema.TOKEN['teks-redup']}; font-size: 11px; margin-top: 6px;")
        lay_hd.addWidget(lbl_zoom_hp)

        self.seg_zoom_hp = komponen.SegmenPilihanAdobe(["100%", "125%", "150%", "175%", "200%"], terpilih=0)
        self.seg_zoom_hp.setToolTip("Naikkan skala render agar aplikasi di HP menggambar lebih tajam sebelum layar diambil")
        lay_hd.addWidget(self.seg_zoom_hp)

        self.btn_apply_hd = komponen.TombolAksiTaktil("Aktifkan HD 2x", jenis_ikon="otomatis")
        self.btn_apply_hd.setToolTip("Menaikkan render resolusi HP 2x via wm size & density")
        self.btn_apply_hd.clicked.connect(self._aksi_terapkan_hd)
        lay_hd.addWidget(self.btn_apply_hd)

        self.btn_reset_hd = komponen.TombolAksiTaktil("Reset Ukuran Layar")
        self.btn_reset_hd.setToolTip("Mengembalikan ukuran layar HP ke standar bawaan")
        self.btn_reset_hd.clicked.connect(self._aksi_reset_hd)
        lay_hd.addWidget(self.btn_reset_hd)

        self.grup_hd.setVisible(False)
        p_device.tambah_widget(self.grup_hd)
        lay.addWidget(p_device)

        # 3. Panel Riwayat Sesi (Galeri Kartu)
        p_riwayat = komponen.PanelAccordionAdobe("Riwayat Foto", terbuka=True)
        self.lbl_total_foto = QLabel("Belum ada foto")
        self.lbl_total_foto.setStyleSheet(f"color: {tema.TOKEN['teks-redup']}; font-weight: 600; font-size: 11px;")
        p_riwayat.tambah_widget(self.lbl_total_foto)

        self.list_riwayat = QListWidget()
        self.list_riwayat.setFixedHeight(180)
        self.list_riwayat.itemDoubleClicked.connect(self._buka_item_riwayat)
        self.list_riwayat.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_riwayat.customContextMenuRequested.connect(self._menu_riwayat)
        self.list_riwayat.setToolTip("Klik dua kali untuk membuka, klik kanan untuk opsi lain")
        p_riwayat.tambah_widget(self.list_riwayat)
        lay.addWidget(p_riwayat)

        # 4. Panel Pemrosesan Massal (Batch Utility)
        p_batch = komponen.PanelAccordionAdobe("Pemrosesan Massal", terbuka=False)
        lbl_batch_info = QLabel("Olah semua tangkapan layar penuh di hasil/layar sekaligus.")
        lbl_batch_info.setWordWrap(True)
        lbl_batch_info.setStyleSheet(f"color: {tema.TOKEN['teks-redup']}; font-size: 11px;")
        p_batch.tambah_widget(lbl_batch_info)

        self.btn_batch_crop = komponen.TombolAksiTaktil("Potong Semua Layar", jenis_ikon="potong")
        self.btn_batch_crop.setToolTip("Membuang status bar dan tombol penampil. Aslinya disalin ke hasil/asli lebih dulu.")
        self.btn_batch_crop.clicked.connect(self._aksi_batch_crop)
        p_batch.tambah_widget(self.btn_batch_crop)

        self.btn_batch_hd = komponen.TombolAksiTaktil("Buat Versi HD 2x Semua", jenis_ikon="otomatis")
        self.btn_batch_hd.setToolTip("Menulis salinan 2x ke hasil/hd. Berkas sumber tidak diubah.")
        self.btn_batch_hd.clicked.connect(self._aksi_batch_hd)
        p_batch.tambah_widget(self.btn_batch_hd)
        lay.addWidget(p_batch)

        lay.addStretch(1)
        scroll.setWidget(konten)
        return scroll

    def _buat_bilah_status(self):
        bar = QFrame()
        bar.setFixedHeight(26)
        bar.setObjectName("bilahStatus")
        bar.setStyleSheet(f"""
            QFrame#bilahStatus {{
                background-color: {tema.TOKEN['latar-bar']};
                border: none;
                border-top: 1px solid {tema.TOKEN['garis']};
            }}
        """)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(12)

        self.status_msg = QLabel("Siap. Sambungkan HP via USB lalu tekan F5 untuk mengambil layar.")
        self.status_msg.setStyleSheet(f"color: {tema.TOKEN['teks-kedua']}; font-size: 11px;")
        lay.addWidget(self.status_msg)

        lay.addStretch(1)

        self.status_zoom = QLabel("Zoom: 100%")
        self.status_zoom.setStyleSheet(f"color: {tema.TOKEN['teks-redup']}; font-size: 11px;")
        lay.addWidget(self.status_zoom)

        return bar

    def _pasang_pintasan(self):
        # F5 = Ambil Layar
        act_f5 = QAction(self)
        act_f5.setShortcut(QKeySequence("F5"))
        act_f5.triggered.connect(self._aksi_ambil_layar)
        self.addAction(act_f5)

        # Enter = Simpan Seleksi
        act_enter = QAction(self)
        act_enter.setShortcut(QKeySequence("Return"))
        act_enter.triggered.connect(self._aksi_simpan_seleksi)
        self.addAction(act_enter)

        # Esc = Hapus Seleksi
        act_esc = QAction(self)
        act_esc.setShortcut(QKeySequence("Escape"))
        act_esc.triggered.connect(self._batal_seleksi)
        self.addAction(act_esc)

        # Ctrl+D = Hapus Seleksi (Adobe standard)
        act_ctrld = QAction(self)
        act_ctrld.setShortcut(QKeySequence("Ctrl+D"))
        act_ctrld.triggered.connect(self._batal_seleksi)
        self.addAction(act_ctrld)

        # Ctrl+A = Pilih Seluruh Layar
        act_ctrla = QAction(self)
        act_ctrla.setShortcut(QKeySequence("Ctrl+A"))
        act_ctrla.triggered.connect(self._pilih_seluruh_layar)
        self.addAction(act_ctrla)

        # M = Seleksi
        act_m = QAction(self)
        act_m.setShortcut(QKeySequence("M"))
        act_m.triggered.connect(lambda: self._ganti_alat("seleksi"))
        self.addAction(act_m)

        # H = Geser
        act_h = QAction(self)
        act_h.setShortcut(QKeySequence("H"))
        act_h.triggered.connect(lambda: self._ganti_alat("geser"))
        self.addAction(act_h)

        # Z = Zoom
        act_z = QAction(self)
        act_z.setShortcut(QKeySequence("Z"))
        act_z.triggered.connect(lambda: self._ganti_alat("zoom"))
        self.addAction(act_z)

        # A = Potong Otomatis
        act_a = QAction(self)
        act_a.setShortcut(QKeySequence("A"))
        act_a.triggered.connect(self._aksi_potong_otomatis)
        self.addAction(act_a)

        # Tab = Toggle Panel Samping
        act_tab = QAction(self)
        act_tab.setShortcut(QKeySequence("Tab"))
        act_tab.triggered.connect(self._toggle_panel_samping)
        self.addAction(act_tab)

        # F11 = Layar Penuh
        act_f11 = QAction(self)
        act_f11.setShortcut(QKeySequence("F11"))
        act_f11.triggered.connect(self._toggle_layar_penuh)
        self.addAction(act_f11)

        for kunci, aksi in [
            ("Ctrl+S", self._aksi_simpan_seleksi),
            ("Ctrl+C", self._aksi_salin),
            ("Ctrl+O", self._aksi_buka_berkas),
            ("Ctrl+0", lambda: self._pada_pilihan_zoom(0, "")),
            ("Ctrl+1", lambda: self._pada_pilihan_zoom(2, "")),
            ("Ctrl+=", lambda: self.kanvas_widget.kanvas.zoom_di(1.25)),
            ("Ctrl++", lambda: self.kanvas_widget.kanvas.zoom_di(1.25)),
            ("Ctrl+-", lambda: self.kanvas_widget.kanvas.zoom_di(0.8)),
            ("F1", self._tampilkan_bantuan),
        ]:
            act = QAction(self)
            act.setShortcut(QKeySequence(kunci))
            act.triggered.connect(aksi)
            self.addAction(act)

    def _toggle_layar_penuh(self):
        if self.isFullScreen():
            self.showMaximized()
            self.btn_fullscreen.jenis_ikon = "layar_penuh"
            self.btn_fullscreen.setToolTip("Beralih ke mode layar penuh (F11)")
            self.btn_fullscreen.set_teks("Layar Penuh")
            self.toast.tampil("Keluar dari Layar Penuh (F11)")
        else:
            self.showFullScreen()
            self.btn_fullscreen.jenis_ikon = "layar_normal"
            self.btn_fullscreen.setToolTip("Keluar dari mode layar penuh (F11 atau Esc)")
            self.btn_fullscreen.set_teks("Keluar Penuh")
            self.toast.tampil("Mode Layar Penuh Aktif (F11)")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.isFullScreen() and not self.kanvas_widget.kanvas.has_sel:
            self._toggle_layar_penuh()
            event.accept()
            return
        super().keyPressEvent(event)

    def _toggle_panel_samping(self):
        visible = not self.panel_kanan.isHidden()
        self.panel_kanan.setVisible(not visible)
        self.btn_toggle_panel.setToolTip("Tampilkan panel samping (Tab)" if visible else "Sembunyikan panel samping (Tab)")

    def _ganti_alat(self, nama):
        self.kanvas_widget.kanvas.alat_aktif = nama
        self.tool_sel.setChecked(nama == "seleksi")
        self.tool_pan.setChecked(nama == "geser")
        self.tool_zoom.setChecked(nama == "zoom")
        if nama == "seleksi":
            self.kanvas_widget.kanvas.setCursor(Qt.CrossCursor)
        elif nama == "geser":
            self.kanvas_widget.kanvas.setCursor(Qt.OpenHandCursor)
        elif nama == "zoom":
            self.kanvas_widget.kanvas.setCursor(Qt.PointingHandCursor)

    def _perbarui_pesan_koneksi(self, status):
        """Mengganti pesan status hanya saat keadaan koneksi berubah."""
        if status == self._status_koneksi:
            return
        self._status_koneksi = status
        if self.pil_layar_saat_ini or self.sedang_mengambil or self.sedang_menyimpan:
            return
        pesan = {
            "device": "HP siap. Tekan F5 untuk mengambil layar.",
            "unauthorized": "Izinkan akses USB debugging di ponsel, lalu coba lagi.",
            "tidak_ada_adb": "adb.exe tidak ditemukan. Letakkan di folder adb/ aplikasi.",
            "offline": "HP offline. Periksa kabel USB.",
        }.get(status, "Siap. Sambungkan HP via USB lalu tekan F5 untuk mengambil layar.")
        self.status_msg.setText(pesan)

    def _perbarui_status_hp(self):
        """Memeriksa HP di benang latar; hasilnya diterapkan oleh _terapkan_status_hp."""
        if self._cek_berjalan:
            return
        self._cek_berjalan = True
        self._jalankan(PekerjaFungsi(_baca_status_hp), self._terapkan_status_hp)

    def _terapkan_status_hp(self, hasil, err):
        self._cek_berjalan = False
        if err or not hasil:
            return
        serial, status, model, info = hasil
        self.serial_hp = serial
        self.info_hp = info

        if status == "device":
            self.nama_model_hp = model
            self.lbl_info_model.setText(self.nama_model_hp)
            self.lbl_info_res.setVisible(True)
            self.lbl_info_dpi.setVisible(True)
            self.grup_hd.setVisible(True)
            if self.info_hp:
                teks_res = f"Resolusi: {self.info_hp['w']} × {self.info_hp['h']} px"
                teks_dpi = f"Kepadatan: {self.info_hp['d']} dpi ({self.info_hp.get('zoom_tampilan', 100)}%)"
                if self.info_hp.get("override"):
                    teks_res += "  ★ Mode HD Aktif"
                self.lbl_info_res.setText(teks_res)
                self.lbl_info_dpi.setText(teks_dpi)
            else:
                self.lbl_info_res.setText("Resolusi: -")
                self.lbl_info_dpi.setText("Kepadatan: -")
            self.lencana_hp.set_status("HP Terhubung", "ok")
            self.lencana_hp.setToolTip(f"{self.nama_model_hp} · {self.serial_hp}\nKlik untuk periksa ulang")
        elif status == "unauthorized":
            self.lbl_info_model.setText("Izinkan akses debugging di ponsel")
            self.lbl_info_res.setVisible(False)
            self.lbl_info_dpi.setVisible(False)
            self.grup_hd.setVisible(False)
            self.lencana_hp.set_status("Otorisasi dibutuhkan", "warn")
            self.lencana_hp.setToolTip("Ketuk Izinkan pada dialog USB debugging di ponsel")
        elif status == "tidak_ada_adb":
            self.lbl_info_model.setText("adb.exe tidak ditemukan")
            self.lbl_info_res.setVisible(False)
            self.lbl_info_dpi.setVisible(False)
            self.grup_hd.setVisible(False)
            self.lencana_hp.set_status("ADB tidak ditemukan", "err")
            self.lencana_hp.setToolTip("Letakkan adb.exe di folder adb/ aplikasi")
        else:
            self.lbl_info_model.setText("Tidak ada perangkat terdeteksi")
            self.lbl_info_res.setVisible(False)
            self.lbl_info_dpi.setVisible(False)
            self.grup_hd.setVisible(False)
            self.lencana_hp.set_status("HP tidak terhubung", "warn")
            self.lencana_hp.setToolTip("Sambungkan kabel USB dan aktifkan USB debugging, lalu klik di sini")

        self._perbarui_pesan_koneksi(status)

    def _aksi_utama(self):
        """Menjalankan aksi yang sedang ditawarkan tombol utama."""
        if self.sedang_mengambil or self.sedang_menyimpan:
            return
        if not self.pil_layar_saat_ini:
            self._aksi_ambil_layar()
        elif not self.kanvas_widget.kanvas.has_sel:
            self._aksi_potong_otomatis()
        else:
            self._aksi_simpan_seleksi()

    def _perbarui_label_dokumen(self):
        if not self.pil_layar_saat_ini:
            self.lbl_dokumen.setText("Belum ada layar")
            return
        w, h = self.pil_layar_saat_ini.size
        z = int(round(self.kanvas_widget.kanvas.skala * 100))
        self.lbl_dokumen.setText(f"{w} × {h} px  ·  {z}%")

    def _perbarui_kontrol(self):
        """Menyelaraskan tombol dan kontrol dengan keadaan layar serta seleksi."""
        k = self.kanvas_widget.kanvas
        ada_gambar = self.pil_layar_saat_ini is not None
        ada_sel = ada_gambar and k.has_sel and k.sel_w >= 10 and k.sel_h >= 10
        sibuk = self.sedang_mengambil or self.sedang_menyimpan or self.sedang_batch

        if not ada_gambar:
            self.btn_utama.set_konten("Ambil Layar HP", "F5", "kamera")
            self.btn_utama.setEnabled(not self.sedang_mengambil)
            self.lbl_petunjuk.setText("Sambungkan ponsel via USB, lalu ambil layar.")
        elif not ada_sel:
            self.btn_utama.set_konten("Pilih Area Foto", "A", "otomatis")
            self.btn_utama.setEnabled(not sibuk)
            self.lbl_petunjuk.setText("Tarik kotak di kanvas, atau gunakan deteksi otomatis.")
        else:
            self.btn_utama.set_konten("Simpan Seleksi", "↵ Enter", "simpan")
            self.btn_utama.setEnabled(not self.sedang_menyimpan)
            self.lbl_petunjuk.setText(f"Area {k.sel_w} × {k.sel_h} px siap disimpan.")

        if self.sedang_menyimpan:
            self.lbl_petunjuk.setText("Menyimpan hasil…")
        elif self.sedang_mengambil and not ada_gambar:
            self.lbl_petunjuk.setText("Mengambil layar dari ponsel…")

        self.btn_ambil_layar.setVisible(ada_gambar)
        self.btn_ambil_layar.setEnabled(not sibuk)
        self.btn_auto.setVisible(ada_sel)
        self.btn_auto.setEnabled(not sibuk)
        self.btn_salin.setVisible(ada_sel)
        self.btn_batch_crop.setEnabled(not sibuk)
        self.btn_batch_hd.setEnabled(not sibuk)
        self.chk_hd.setVisible(ada_gambar)
        self.chk_raw.setVisible(ada_gambar)

        self.cmb_rasio.setEnabled(ada_gambar)
        self.seg_zoom.setEnabled(ada_gambar)
        self.btn_pilih_semua.setEnabled(ada_gambar and not sibuk)
        self.btn_hapus_seleksi.setEnabled(ada_sel and not sibuk)

    def _pada_seleksi_berubah(self, x, y, w, h):
        self.box_dimensi.set_dimensi(w, h)
        self._perbarui_kontrol()

    def _pada_zoom_berubah(self, persen):
        self.status_zoom.setText(f"Zoom: {persen}%")
        k = self.kanvas_widget.kanvas
        if k.mode_pas:
            idx = 0
        elif abs(k.skala - 0.5) < 0.01:
            idx = 1
        elif abs(k.skala - 1.0) < 0.01:
            idx = 2
        elif abs(k.skala - 2.0) < 0.01:
            idx = 3
        else:
            idx = -1
        self.seg_zoom.set_aktif(idx)
        self._perbarui_label_dokumen()

    def _pada_pilihan_zoom(self, idx, teks):
        if idx == 0:
            self.kanvas_widget.kanvas.atur_zoom(0.0)
        elif idx == 1:
            self.kanvas_widget.kanvas.atur_zoom(0.5)
        elif idx == 2:
            self.kanvas_widget.kanvas.atur_zoom(1.0)
        elif idx == 3:
            self.kanvas_widget.kanvas.atur_zoom(2.0)

    def _pada_pilihan_rasio(self, idx):
        rasio_map = {
            0: None,
            1: 1.0,
            2: 3.0 / 4.0,
            3: 4.0 / 5.0,
            4: 9.0 / 16.0,
            5: 16.0 / 9.0,
        }
        self.kanvas_widget.kanvas.set_rasio_kunci(rasio_map.get(idx))

    def _batal_seleksi(self):
        self.kanvas_widget.kanvas.hapus_seleksi()

    def _pilih_seluruh_layar(self):
        if self.pil_layar_saat_ini:
            w, h = self.pil_layar_saat_ini.size
            self.kanvas_widget.kanvas.set_seleksi_piksel(0, 0, w, h)

    def _aksi_ambil_layar(self):
        if self.sedang_mengambil or self.sedang_menyimpan:
            return

        self.sedang_mengambil = True
        self.btn_ambil_layar.setEnabled(False)
        self.tool_cap.setEnabled(False)
        self.status_msg.setText("Mengambil layar dari ponsel…")
        self._perbarui_kontrol()
        self._jalankan(PekerjaAmbilLayar(), self._selesai_ambil_layar)

    def _selesai_ambil_layar(self, raw_png, err):
        self.sedang_mengambil = False
        self.tool_cap.setEnabled(True)

        if err or not raw_png:
            self.status_msg.setText(f"Gagal mengambil layar: {err or 'Data kosong'}")
            self.toast.tampil(f"Gagal: {err or 'Data kosong'}", sukses=False)
            self._perbarui_kontrol()
            self._perbarui_status_hp()
            return
        self._muat_gambar(raw_png, "Layar")

    def _muat_gambar(self, data, sumber):
        """Memuat bytes gambar (dari HP atau berkas) ke kanvas."""
        try:
            pil = Image.open(io.BytesIO(data))
            pil.load()
            pix = QPixmap()
            if not pix.loadFromData(data):
                raise ValueError("format gambar tidak didukung")
        except Exception as e:
            self.status_msg.setText(f"Gagal memuat gambar: {e}")
            self.toast.tampil("Gambar tidak bisa dibuka", sukses=False)
            self._perbarui_kontrol()
            return
        self.pil_layar_saat_ini = pil
        self.pixmap_saat_ini = pix
        self.setWindowTitle(f"{sumber} — Phone Capture Studio")
        self.kanvas_widget.kanvas.set_gambar(pix)
        w, h = pil.size
        self._perbarui_label_dokumen()
        self.status_msg.setText(f"{sumber} {w}×{h} px dimuat. Tarik kotak pada area yang ingin disimpan, atau tekan A.")
        self.toast.tampil(f"{sumber} {w}×{h} px dimuat")
        self._perbarui_kontrol()
        self.kanvas_widget.kanvas.setFocus()

    def _aksi_buka_berkas(self):
        if self.sedang_mengambil or self.sedang_menyimpan:
            return
        jalur, _ = QFileDialog.getOpenFileName(
            self, "Buka gambar", lokasi.folder_layar_penuh(),
            "Gambar (*.png *.jpg *.jpeg *.webp *.bmp)")
        if jalur:
            self._buka_berkas(jalur)

    def _buka_berkas(self, jalur):
        try:
            with open(jalur, "rb") as f:
                data = f.read()
        except OSError as e:
            self.toast.tampil(f"Gagal membuka: {e}", sukses=False)
            return
        self._muat_gambar(data, os.path.basename(jalur))

    def _jalur_dari_drop(self, event):
        md = event.mimeData()
        if md.hasUrls():
            for url in md.urls():
                jalur = url.toLocalFile()
                if jalur.lower().endswith(EKSTENSI_GAMBAR):
                    return jalur
        return None

    def dragEnterEvent(self, event):
        if self._jalur_dari_drop(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        jalur = self._jalur_dari_drop(event)
        if jalur:
            event.acceptProposedAction()
            self._buka_berkas(jalur)

    def _aksi_salin(self):
        if not self.pixmap_saat_ini:
            return
        k = self.kanvas_widget.kanvas
        if k.has_sel and k.sel_w >= 10 and k.sel_h >= 10:
            pix = self.pixmap_saat_ini.copy(k.sel_x, k.sel_y, k.sel_w, k.sel_h)
        else:
            pix = self.pixmap_saat_ini
        QApplication.clipboard().setPixmap(pix)
        self.status_msg.setText(f"{pix.width()}×{pix.height()} px disalin ke clipboard. Tempel dengan Ctrl+V.")
        self.toast.tampil("Disalin ke clipboard")

    def _jalankan(self, pekerja, slot):
        """Menyimpan referensi benang sampai selesai agar tidak dihancurkan saat berjalan."""
        self._pekerja.add(pekerja)
        pekerja.selesai.connect(slot)
        pekerja.finished.connect(lambda: self._pekerja.discard(pekerja))
        pekerja.start()
        return pekerja

    def _aksi_simpan_seleksi(self):
        if self.sedang_menyimpan or self.sedang_mengambil:
            return
        if not self.pil_layar_saat_ini:
            self.status_msg.setText("Peringatan: Ambil layar (F5) terlebih dahulu.")
            self.toast.tampil("Ambil layar (F5) terlebih dahulu", sukses=False)
            return

        k = self.kanvas_widget.kanvas
        if not k.has_sel or k.sel_w < 10 or k.sel_h < 10:
            self.status_msg.setText("Peringatan: Tarik kotak seleksi pada area foto terlebih dahulu.")
            self.toast.tampil("Tarik kotak seleksi terlebih dahulu", sukses=False)
            return

        self.sedang_menyimpan = True
        self.status_msg.setText("Menyimpan dan memproses citra...")
        self._perbarui_kontrol()

        box = (k.sel_x, k.sel_y, k.sel_w, k.sel_h)
        buat_hd = self.chk_hd.isChecked()
        simpan_raw = self.chk_raw.isChecked()

        self._jalankan(PekerjaSimpan(self.pil_layar_saat_ini, box, buat_hd=buat_hd, simpan_raw=simpan_raw),
                       self._selesai_simpan)

    def _selesai_simpan(self, hasil, err):
        self.sedang_menyimpan = False
        self._perbarui_kontrol()

        if err or not hasil:
            self.status_msg.setText(f"Gagal menyimpan: {err}")
            self.toast.tampil(f"Gagal: {err}", sukses=False)
            return

        self._tambah_item_riwayat(hasil)
        teks_hd = " (+ versi HD 2x)" if hasil.get("jalur_hd") else ""
        self.status_msg.setText(f"Tersimpan: {hasil['nama']} ({hasil['w']}×{hasil['h']} px){teks_hd}")
        self.toast.tampil(f"{hasil['nama']} tersimpan ({hasil['w']}×{hasil['h']} px)")

    def _aksi_potong_otomatis(self):
        if self.sedang_mengambil or self.sedang_menyimpan:
            return
        if not self.pil_layar_saat_ini:
            self._aksi_ambil_layar()
            return

        x, y, w, h = processor.deteksi_kotak_foto(self.pil_layar_saat_ini)
        if w > 50 and h > 50:
            self.kanvas_widget.kanvas.set_seleksi_piksel(x, y, w, h)
            self.status_msg.setText(f"Deteksi otomatis: {w}×{h} px. Rapikan dengan panah/pegangan, lalu Enter.")
            self.toast.tampil(f"Batas foto terdeteksi: {w}×{h} px")
            self.kanvas_widget.kanvas.setFocus()
        else:
            self.status_msg.setText("Deteksi batas otomatis gagal. Silakan tarik kotak secara manual.")
            self.toast.tampil("Deteksi batas otomatis gagal", sukses=False)

    def _aksi_terapkan_hd(self):
        if not self.serial_hp:
            self.toast.tampil("HP tidak terhubung", sukses=False)
            return
        skala = [1.0, 1.25, 1.5, 1.75, 2.0][max(0, self.seg_zoom_hp.indeks_aktif)]
        self.btn_apply_hd.setEnabled(False)
        self.btn_reset_hd.setEnabled(False)
        self.status_msg.setText("Menerapkan mode HD di ponsel…")
        self._jalankan(PekerjaFungsi(adb.terapkan_hd, self.serial_hp, skala), self._selesai_hd)

    def _selesai_hd(self, hasil, err):
        self.btn_apply_hd.setEnabled(True)
        self.btn_reset_hd.setEnabled(True)
        ok, msg = hasil if hasil else (False, err or "tidak diketahui")
        if ok:
            self.status_msg.setText(f"{msg}. Tunggu layar HP stabil, lalu tekan F5.")
            self.toast.tampil("Mode HD aktif")
        else:
            self.status_msg.setText(f"Gagal: {msg}")
            self.toast.tampil(f"Gagal: {msg}", sukses=False)
        self._perbarui_status_hp()

    def _aksi_reset_hd(self):
        if not self.serial_hp:
            self.toast.tampil("HP tidak terhubung", sukses=False)
            return
        self.btn_apply_hd.setEnabled(False)
        self.btn_reset_hd.setEnabled(False)
        self._jalankan(PekerjaFungsi(adb.reset_layar, self.serial_hp), self._selesai_reset_hd)

    def _selesai_reset_hd(self, hasil, err):
        self.btn_apply_hd.setEnabled(True)
        self.btn_reset_hd.setEnabled(True)
        self.status_msg.setText(hasil[1] if hasil else f"Gagal: {err}")
        if hasil:
            self.toast.tampil("Layar ponsel kembali normal")
        self._perbarui_status_hp()

    def _aksi_batch_crop(self):
        if self.sedang_batch:
            return
        folder_layar = lokasi.folder_layar_penuh()
        berkas = [f for f in os.listdir(folder_layar) if f.lower().endswith(".png")]
        if not berkas:
            QMessageBox.information(self, "Potong Semua Layar", f"Tidak ada berkas PNG di\n{folder_layar}")
            return
        jawab = QMessageBox.question(
            self,
            "Potong Semua Layar",
            f"{len(berkas)} berkas di hasil/layar akan diperiksa. Yang masih berupa layar penuh dipotong "
            "dan ditimpa; salinan aslinya disimpan di hasil/asli.\n\nLanjutkan?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if jawab != QMessageBox.Yes:
            return
        self._mulai_batch("Memotong", PekerjaFungsi(_potong_massal, folder_layar, lokasi.folder_layar_asli(),
                                                     dengan_kemajuan=True), self._selesai_batch_crop)

    def _mulai_batch(self, kata, pekerja, slot):
        self.sedang_batch = True
        self._perbarui_kontrol()
        pekerja.kemajuan.connect(lambda i, n: self.status_msg.setText(f"{kata} {i} dari {n}…"))
        self._jalankan(pekerja, slot)

    def _selesai_batch_crop(self, hasil, err):
        self.sedang_batch = False
        self._perbarui_kontrol()
        if err or not hasil:
            self.status_msg.setText(f"Pemotongan gagal: {err}")
            self.toast.tampil("Pemotongan massal gagal", sukses=False)
            return
        teks = f"{hasil['dipotong']} dipotong, {hasil['dilewati']} dilewati"
        if hasil["gagal"]:
            teks += f", {hasil['gagal']} gagal"
        self.status_msg.setText(f"Pemotongan selesai: {teks} (dari {hasil['total']} berkas).")
        self.toast.tampil(f"Selesai: {teks}", sukses=not hasil["gagal"])

    def _aksi_batch_hd(self):
        if self.sedang_batch:
            return
        folder_layar = lokasi.folder_layar_penuh()
        berkas = [f for f in os.listdir(folder_layar) if f.lower().endswith(".png")]
        if not berkas:
            QMessageBox.information(self, "Buat Versi HD", f"Tidak ada berkas PNG di\n{folder_layar}")
            return
        self._mulai_batch("Membuat versi HD", PekerjaFungsi(_hd_massal, folder_layar, lokasi.folder_layar_hd(),
                                                            dengan_kemajuan=True), self._selesai_batch_hd)

    def _selesai_batch_hd(self, hasil, err):
        self.sedang_batch = False
        self._perbarui_kontrol()
        if err or not hasil:
            self.status_msg.setText(f"Gagal membuat versi HD: {err}")
            self.toast.tampil("Gagal membuat versi HD", sukses=False)
            return
        self.status_msg.setText(f"{hasil['dibuat']} versi HD dibuat di hasil/hd"
                                + (f", {hasil['gagal']} gagal." if hasil["gagal"] else "."))
        self.toast.tampil(f"{hasil['dibuat']} versi HD dibuat", sukses=not hasil["gagal"])

    def _perbarui_total_foto(self, jumlah):
        if jumlah:
            self.lbl_total_foto.setText(f"{jumlah} foto tersimpan")
            self.lbl_total_foto.setStyleSheet(f"color: {tema.TOKEN['status-ok']}; font-weight: 600; font-size: 11px;")
        else:
            self.lbl_total_foto.setText("Belum ada foto")
            self.lbl_total_foto.setStyleSheet(f"color: {tema.TOKEN['teks-redup']}; font-weight: 600; font-size: 11px;")

    def _muat_riwayat_awal(self):
        folder = lokasi.folder_hasil()
        if not os.path.isdir(folder):
            return
        berkas = sorted([f for f in os.listdir(folder) if f.startswith("foto_") and f.endswith(".png")])
        self._total_foto = len(berkas)
        self._perbarui_total_foto(self._total_foto)
        if not berkas:
            self.list_riwayat.setFixedHeight(84)
            item = QListWidgetItem()
            item.setSizeHint(QSize(240, 48))
            item.setFlags(Qt.NoItemFlags)
            lbl_kosong = QLabel("Foto yang disimpan akan muncul di sini.")
            lbl_kosong.setAlignment(Qt.AlignCenter)
            lbl_kosong.setStyleSheet(f"color: {tema.TOKEN['teks-redup']}; font-size: 11px; padding: 12px;")
            self.list_riwayat.addItem(item)
            self.list_riwayat.setItemWidget(item, lbl_kosong)
            return

        self.list_riwayat.setFixedHeight(180)
        for f in reversed(berkas[-20:]):
            jalur = os.path.join(folder, f)
            item = QListWidgetItem()
            item.setSizeHint(QSize(240, 56))
            item.setData(Qt.UserRole, jalur)
            kartu = komponen.KartuRiwayatItem(f, jalur)
            self.list_riwayat.addItem(item)
            self.list_riwayat.setItemWidget(item, kartu)

    def _tambah_item_riwayat(self, hasil):
        if self.list_riwayat.count() == 1 and not self.list_riwayat.item(0).data(Qt.UserRole):
            self.list_riwayat.takeItem(0)

        item = QListWidgetItem()
        item.setSizeHint(QSize(240, 56))
        item.setData(Qt.UserRole, hasil["jalur"])
        kartu = komponen.KartuRiwayatItem(hasil["nama"], hasil["jalur"])
        self.list_riwayat.setFixedHeight(180)
        self.list_riwayat.insertItem(0, item)
        self.list_riwayat.setItemWidget(item, kartu)
        while self.list_riwayat.count() > 20:
            self.list_riwayat.takeItem(self.list_riwayat.count() - 1)
        self._total_foto += 1
        self._perbarui_total_foto(self._total_foto)

    def _buka_item_riwayat(self, item):
        jalur = item.data(Qt.UserRole)
        if jalur and os.path.isfile(jalur):
            os.startfile(jalur)

    def _menu_riwayat(self, pos):
        item = self.list_riwayat.itemAt(pos)
        jalur = item.data(Qt.UserRole) if item else None
        if not jalur or not os.path.isfile(jalur):
            return
        menu = QMenu(self)
        menu.addAction("Buka", lambda: os.startfile(jalur))
        menu.addAction("Tampilkan di folder", lambda: subprocess.Popen(f'explorer /select,"{os.path.normpath(jalur)}"'))
        menu.addAction("Salin gambar", lambda: (QApplication.clipboard().setPixmap(QPixmap(jalur)),
                                                self.toast.tampil("Disalin ke clipboard")))
        menu.addAction("Muat ke kanvas", lambda: self._buka_berkas(jalur))
        menu.exec(self.list_riwayat.viewport().mapToGlobal(pos))

    def _tampilkan_bantuan(self):
        baris = [
            ("F5", "Ambil layar HP"), ("Ctrl+O", "Buka gambar dari PC"),
            ("Seret", "Buat seleksi; tarik pegangan untuk mengubah ukuran"),
            ("Enter / Ctrl+S", "Simpan seleksi"), ("Ctrl+C", "Salin seleksi ke clipboard"),
            ("A", "Pilih area foto otomatis"), ("Ctrl+A", "Pilih seluruh layar"),
            ("Esc / Ctrl+D", "Hapus seleksi"), ("Panah", "Geser seleksi 1 px (Shift: 10 px)"),
            ("M / H / Z", "Alat seleksi, geser, zoom (Alt+klik: perkecil)"),
            ("Spasi (tahan)", "Geser kanvas sementara"), ("Klik kanan + seret", "Geser kanvas"),
            ("Ctrl+scroll", "Zoom di posisi kursor"), ("Ctrl+0 / Ctrl+1", "Pas layar / 100%"),
            ("Ctrl+ + / Ctrl+ -", "Perbesar / perkecil"),
            ("Tab", "Tampilkan atau sembunyikan panel"), ("F11", "Layar penuh"),
        ]
        isi = "".join(f"<tr><td style='padding:3px 18px 3px 0'><b>{k}</b></td><td>{v}</td></tr>" for k, v in baris)
        QMessageBox.information(self, "Pintasan keyboard", f"<table>{isi}</table>")

    def _muat_pengaturan(self):
        st = QSettings()
        self.chk_hd.setChecked(st.value("simpan/hd", True, type=bool))
        self.chk_raw.setChecked(st.value("simpan/layar_penuh", False, type=bool))
        idx_rasio = st.value("seleksi/rasio", 0, type=int)
        if 0 <= idx_rasio < self.cmb_rasio.count():
            self.cmb_rasio.setCurrentIndex(idx_rasio)
        idx_hp = st.value("hd/skala", 0, type=int)
        if 0 <= idx_hp < len(self.seg_zoom_hp.tombol_list):
            self.seg_zoom_hp.set_aktif(idx_hp)
        if not st.value("tampilan/panel", True, type=bool):
            self._toggle_panel_samping()

    def _simpan_pengaturan(self):
        st = QSettings()
        st.setValue("simpan/hd", self.chk_hd.isChecked())
        st.setValue("simpan/layar_penuh", self.chk_raw.isChecked())
        st.setValue("seleksi/rasio", self.cmb_rasio.currentIndex())
        st.setValue("hd/skala", self.seg_zoom_hp.indeks_aktif)
        st.setValue("tampilan/panel", not self.panel_kanan.isHidden())

    def closeEvent(self, event):
        if self.sedang_batch or self.sedang_menyimpan:
            QMessageBox.information(self, "Phone Capture Studio", "Tunggu sampai proses yang berjalan selesai.")
            event.ignore()
            return
        if self.serial_hp:
            info = adb.info_layar(self.serial_hp)
            if info and info.get("override"):
                tanya = QMessageBox.question(
                    self,
                    "Phone Capture Studio",
                    f"Layar ponsel masih memakai mode HD ({info['w']}×{info['h']}, {info['d']} dpi).\n\n"
                    "Kembalikan resolusi ponsel ke normal sekarang?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Yes,
                )
                if tanya == QMessageBox.Cancel:
                    event.ignore()
                    return
                elif tanya == QMessageBox.Yes:
                    adb.reset_layar(self.serial_hp)
        self._simpan_pengaturan()
        self.timer_status.stop()
        for t in list(self._pekerja):
            t.wait(5000)
        event.accept()
