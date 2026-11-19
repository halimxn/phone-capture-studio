"""Komponen visual presisi, luwes, dan taktil bergaya clean design Adobe Spectrum."""
import math
from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, Signal, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from . import tema


def _lukis_cincin_fokus(p, rect, radius):
    """Cincin fokus titik-titik agar tidak tertukar dengan keadaan terpilih."""
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 150), 1, Qt.DotLine))
    p.drawRoundedRect(rect.adjusted(1.5, 1.5, -1.5, -1.5), radius, radius)


def lukis_ikon_vektor(p, jenis, cx, cy, warna, sz=16):
    """Menggambar ikon garis vektor presisi anti-aliasing dengan proporsi seimbang."""
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(warna, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    hs = sz / 2.0

    if jenis == "seleksi":
        pen_dash = QPen(warna, 1.3, Qt.CustomDashLine)
        pen_dash.setDashPattern([3, 2.5])
        p.setPen(pen_dash)
        p.drawRect(QRectF(cx - hs + 1, cy - hs + 1, sz - 2, sz - 2))
    elif jenis == "geser":
        # Ikon Geser / Pan 4 Arah (Cross Pan) yang sangat bersih & presisi
        p.drawLine(QPointF(cx - 6, cy), QPointF(cx + 6, cy))
        p.drawLine(QPointF(cx, cy - 6), QPointF(cx, cy + 6))
        # Panah kiri, kanan, atas, bawah
        p.drawLine(QPointF(cx - 6, cy), QPointF(cx - 3.5, cy - 2.5))
        p.drawLine(QPointF(cx - 6, cy), QPointF(cx - 3.5, cy + 2.5))
        p.drawLine(QPointF(cx + 6, cy), QPointF(cx + 3.5, cy - 2.5))
        p.drawLine(QPointF(cx + 6, cy), QPointF(cx + 3.5, cy + 2.5))
        p.drawLine(QPointF(cx, cy - 6), QPointF(cx - 2.5, cy - 3.5))
        p.drawLine(QPointF(cx, cy - 6), QPointF(cx + 2.5, cy - 3.5))
        p.drawLine(QPointF(cx, cy + 6), QPointF(cx - 2.5, cy + 3.5))
        p.drawLine(QPointF(cx, cy + 6), QPointF(cx + 2.5, cy + 3.5))
    elif jenis == "zoom":
        p.drawEllipse(QPointF(cx - 2, cy - 2), 5, 5)
        p.drawLine(QPointF(cx + 2, cy + 2), QPointF(cx + 6.5, cy + 6.5))
    elif jenis == "potong":
        p.drawLine(QPointF(cx - hs, cy - 3), QPointF(cx + 3, cy - 3))
        p.drawLine(QPointF(cx - 3, cy - hs), QPointF(cx - 3, cy + 3))
        p.drawLine(QPointF(cx - 3, cy + 3), QPointF(cx + hs, cy + 3))
        p.drawLine(QPointF(cx + 3, cy - 3), QPointF(cx + 3, cy + hs))
    elif jenis == "kamera":
        p.drawRoundedRect(QRectF(cx - 7, cy - 4, 14, 11), 2, 2)
        p.drawEllipse(QPointF(cx, cy + 1.5), 3, 3)
        p.drawLine(QPointF(cx - 4, cy - 4), QPointF(cx - 2, cy - 6))
        p.drawLine(QPointF(cx - 2, cy - 6), QPointF(cx + 2, cy - 6))
        p.drawLine(QPointF(cx + 2, cy - 6), QPointF(cx + 4, cy - 4))
    elif jenis == "simpan":
        p.drawRoundedRect(QRectF(cx - 6.5, cy - 6.5, 13, 13), 2, 2)
        p.fillRect(QRectF(cx - 4, cy - 6.5, 8, 4), warna)
        p.drawRect(QRectF(cx - 4.5, cy - 0.5, 9, 6))
    elif jenis == "folder":
        path = QPainterPath()
        path.moveTo(cx - 7, cy - 4)
        path.lineTo(cx - 3, cy - 4)
        path.lineTo(cx - 1, cy - 2)
        path.lineTo(cx + 7, cy - 2)
        path.lineTo(cx + 7, cy + 5)
        path.lineTo(cx - 7, cy + 5)
        path.closeSubpath()
        p.drawPath(path)
    elif jenis == "layar_penuh":
        p.drawLine(QPointF(cx - 6, cy - 3), QPointF(cx - 6, cy - 6))
        p.drawLine(QPointF(cx - 6, cy - 6), QPointF(cx - 3, cy - 6))
        p.drawLine(QPointF(cx + 3, cy - 6), QPointF(cx + 6, cy - 6))
        p.drawLine(QPointF(cx + 6, cy - 6), QPointF(cx + 6, cy - 3))
        p.drawLine(QPointF(cx - 6, cy + 3), QPointF(cx - 6, cy + 6))
        p.drawLine(QPointF(cx - 6, cy + 6), QPointF(cx - 3, cy + 6))
        p.drawLine(QPointF(cx + 3, cy + 6), QPointF(cx + 6, cy + 6))
        p.drawLine(QPointF(cx + 6, cy + 6), QPointF(cx + 6, cy + 3))
    elif jenis == "layar_normal":
        p.drawLine(QPointF(cx - 3, cy - 6), QPointF(cx - 3, cy - 3))
        p.drawLine(QPointF(cx - 3, cy - 3), QPointF(cx - 6, cy - 3))
        p.drawLine(QPointF(cx + 3, cy - 6), QPointF(cx + 3, cy - 3))
        p.drawLine(QPointF(cx + 3, cy - 3), QPointF(cx + 6, cy - 3))
        p.drawLine(QPointF(cx - 3, cy + 6), QPointF(cx - 3, cy + 3))
        p.drawLine(QPointF(cx - 3, cy + 3), QPointF(cx - 6, cy + 3))
        p.drawLine(QPointF(cx + 3, cy + 6), QPointF(cx + 3, cy + 3))
        p.drawLine(QPointF(cx + 6, cy + 3), QPointF(cx + 3, cy + 3))
    elif jenis == "panel":
        p.drawRoundedRect(QRectF(cx - 6, cy - 5, 12, 10), 2, 2)
        p.drawLine(QPointF(cx + 1, cy - 5), QPointF(cx + 1, cy + 5))
    elif jenis == "otomatis":
        p.drawLine(QPointF(cx, cy - 6), QPointF(cx, cy + 6))
        p.drawLine(QPointF(cx - 6, cy), QPointF(cx + 6, cy))
        p.drawLine(QPointF(cx - 4, cy - 4), QPointF(cx + 4, cy + 4))
        p.drawLine(QPointF(cx - 4, cy + 4), QPointF(cx + 4, cy - 4))


class TombolAksiHero(QPushButton):
    """Tombol aksi utama (CTA Hero) dengan pencahayaan halus, ikon vektor, dan lencana pintasan kbd."""

    def __init__(self, teks="Simpan Area Terpilih", shortcut="↵ Enter", jenis_ikon="simpan", parent=None):
        super().__init__(teks, parent)
        self.teks = teks
        self.shortcut = shortcut
        self.jenis_ikon = jenis_ikon
        self.setFixedHeight(38)
        self.setCursor(Qt.PointingHandCursor)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(20, 115, 230, 85))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

    def sizeHint(self):
        fm = self.fontMetrics()
        tw = fm.horizontalAdvance(self.teks)
        iw = 24 if self.jenis_ikon else 0
        kw = (fm.horizontalAdvance(self.shortcut) + 16) if self.shortcut else 0
        return QSize(tw + iw + kw + 36, 38)

    def set_konten(self, teks, shortcut="", jenis_ikon=None):
        """Mengganti aksi utama sesuai langkah berikutnya tanpa membuat tombol baru."""
        if (self.teks, self.shortcut, self.jenis_ikon) == (teks, shortcut, jenis_ikon):
            return
        self.teks = teks
        self.shortcut = shortcut
        self.jenis_ikon = jenis_ikon
        self.setText(teks)
        self.updateGeometry()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()
        is_pressed = self.isDown()
        is_hover = self.underMouse()
        is_disabled = not self.isEnabled()

        y_offset = 1 if is_pressed else 0
        rect = QRectF(0, y_offset, w, h - y_offset)

        grad = QLinearGradient(0, 0, 0, h)
        if is_disabled:
            grad.setColorAt(0, QColor("#262626"))
            grad.setColorAt(1, QColor("#1e1e1e"))
            pen_border = QPen(QColor(255, 255, 255, 18), 1)
        elif is_pressed:
            grad.setColorAt(0, QColor(tema.TOKEN["aksen-tekan"]))
            grad.setColorAt(1, QColor("#08459a"))
            pen_border = QPen(QColor("#07387d"), 1)
        elif is_hover:
            grad.setColorAt(0, QColor(tema.TOKEN["aksen-hover-atas"]))
            grad.setColorAt(1, QColor(tema.TOKEN["aksen-hover-bawah"]))
            pen_border = QPen(QColor("#2482ff"), 1)
        else:
            grad.setColorAt(0, QColor(tema.TOKEN["aksen-atas"]))
            grad.setColorAt(1, QColor(tema.TOKEN["aksen-bawah"]))
            pen_border = QPen(QColor(tema.TOKEN["aksen"]), 1)

        p.setBrush(QBrush(grad))
        p.setPen(pen_border)
        p.drawRoundedRect(rect, 7, 7)

        if not is_disabled and not is_pressed:
            p.setPen(QPen(QColor(255, 255, 255, 50 if is_hover else 30), 1))
            p.drawLine(QPointF(8, 1), QPointF(w - 8, 1))

        warna_konten = QColor("#6f6f6f" if is_disabled else "#ffffff")
        if self.jenis_ikon:
            lukis_ikon_vektor(p, self.jenis_ikon, 20, (h / 2.0) + y_offset, warna_konten, sz=15)

        fm = p.fontMetrics()
        kw = (fm.horizontalAdvance(self.shortcut) + 14) if self.shortcut else 0

        p.setFont(self.font())
        font_teks = QFont(self.font())
        font_teks.setBold(True)
        p.setFont(font_teks)
        p.setPen(warna_konten)
        start_x = 36 if self.jenis_ikon else 14
        rect_teks = QRect(start_x, y_offset, w - start_x - kw - 16, h)
        p.drawText(rect_teks, Qt.AlignVCenter | Qt.AlignLeft, self.teks)

        if self.shortcut:
            font_kbd = QFont(self.font())
            if self.font().pixelSize() > 0:
                font_kbd.setPixelSize(max(9, self.font().pixelSize() - 2))
            else:
                font_kbd.setPointSize(max(7, self.font().pointSize() - 1))
            font_kbd.setBold(True)
            p.setFont(font_kbd)
            fm_k = p.fontMetrics()
            kw_box = fm_k.horizontalAdvance(self.shortcut) + 12
            kh_box = 20
            kx = w - kw_box - 10
            ky = int((h - kh_box) / 2.0) + y_offset

            p.setBrush(QColor(0, 0, 0, 60))
            p.setPen(QPen(QColor(255, 255, 255, 30), 1))
            p.drawRoundedRect(QRectF(kx, ky, kw_box, kh_box), 4, 4)

            p.setPen(QColor("#dceaff"))
            p.drawText(QRect(kx, ky, kw_box, kh_box), Qt.AlignCenter, self.shortcut)

        if self.hasFocus():
            _lukis_cincin_fokus(p, rect, 7)


class TombolAksiTaktil(QPushButton):
    """Tombol aksi sekunder luwes dengan sizeHint presisi agar teks tidak pernah terpotong."""

    def __init__(self, teks, shortcut="", jenis_ikon=None, parent=None):
        super().__init__(teks, parent)
        self.teks = teks
        self.shortcut = shortcut
        self.jenis_ikon = jenis_ikon
        self.setFixedHeight(32)
        self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self):
        fm = self.fontMetrics()
        tw = fm.horizontalAdvance(self.teks)
        iw = 24 if self.jenis_ikon else 0
        kw = (fm.horizontalAdvance(self.shortcut) + 16) if self.shortcut else 0
        return QSize(tw + iw + kw + 24, 32)

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()
        is_pressed = self.isDown()
        is_hover = self.underMouse()
        is_disabled = not self.isEnabled()

        y_offset = 1 if is_pressed else 0
        rect = QRectF(0, y_offset, w, h - y_offset)

        if is_disabled:
            p.setBrush(QColor(255, 255, 255, 6))
            p.setPen(Qt.NoPen)
        elif is_pressed:
            p.setBrush(QColor(255, 255, 255, 12))
            p.setPen(QPen(QColor(255, 255, 255, 18), 1))
        elif is_hover:
            p.setBrush(QColor(255, 255, 255, 22))
            p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        else:
            p.setBrush(QColor(255, 255, 255, 12))
            p.setPen(QPen(QColor(255, 255, 255, 18), 1))

        p.drawRoundedRect(rect, 6, 6)

        warna_teks = QColor(tema.TOKEN["teks-mati"] if is_disabled else ("#ffffff" if is_hover else tema.TOKEN["teks-utama"]))
        if self.jenis_ikon:
            lukis_ikon_vektor(p, self.jenis_ikon, 16, (h / 2.0) + y_offset, warna_teks, sz=14)

        p.setFont(self.font())
        fm = p.fontMetrics()
        kw_total = (fm.horizontalAdvance(self.shortcut) + 14) if self.shortcut else 0

        p.setPen(warna_teks)
        start_x = 30 if self.jenis_ikon else 10
        rect_teks = QRect(start_x, y_offset, w - start_x - kw_total - 10, h)
        p.drawText(rect_teks, Qt.AlignVCenter | (Qt.AlignLeft if (self.jenis_ikon or self.shortcut) else Qt.AlignCenter), self.teks)

        if self.shortcut:
            font_kbd = QFont(self.font())
            if self.font().pixelSize() > 0:
                font_kbd.setPixelSize(max(9, self.font().pixelSize() - 2))
            else:
                font_kbd.setPointSize(max(7, self.font().pointSize() - 1))
            font_kbd.setBold(True)
            p.setFont(font_kbd)
            fm_k = p.fontMetrics()
            kw = fm_k.horizontalAdvance(self.shortcut) + 8
            kh = 17
            kx = w - kw - 8
            ky = int((h - kh) / 2.0) + y_offset

            p.setBrush(QColor(255, 255, 255, 14))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(kx, ky, kw, kh), 3, 3)

            p.setPen(QColor(tema.TOKEN["teks-redup"] if is_disabled else tema.TOKEN["teks-kedua"]))
            p.drawText(QRect(kx, ky, kw, kh), Qt.AlignCenter, self.shortcut)

        if self.hasFocus():
            _lukis_cincin_fokus(p, rect, 6)


class TombolChipAksi(QPushButton):
    """Tombol ghost / flat ramping untuk bilah atas dengan kalkulasi lebar dinamis tanpa teks terpotong."""

    def __init__(self, teks="", jenis_ikon=None, tip="", parent=None):
        super().__init__(teks, parent)
        self.teks = teks
        self.jenis_ikon = jenis_ikon
        self.setFixedHeight(28)
        self.setCursor(Qt.PointingHandCursor)
        if tip:
            self.setToolTip(tip)

    def set_teks(self, teks):
        self.teks = teks
        self.setText(teks)
        self.updateGeometry()
        self.update()

    def sizeHint(self):
        fm = self.fontMetrics()
        tw = fm.horizontalAdvance(self.teks) if self.teks else 0
        iw = 20 if self.jenis_ikon else 0
        spacing = 6 if (self.teks and self.jenis_ikon) else 0
        pad = 22 if self.teks else 10
        return QSize(tw + iw + spacing + pad, 28)

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()
        is_pressed = self.isDown()
        is_hover = self.underMouse()
        is_disabled = not self.isEnabled()

        y_offset = 1 if is_pressed else 0
        rect = QRectF(0, y_offset, w, h - y_offset)

        if is_disabled:
            p.setBrush(Qt.NoBrush)
        elif is_pressed:
            p.setBrush(QColor(255, 255, 255, 25))
        elif is_hover:
            p.setBrush(QColor(255, 255, 255, 16))
        else:
            p.setBrush(Qt.NoBrush)

        p.setPen(Qt.NoPen)
        p.drawRoundedRect(rect, 6, 6)

        warna = QColor(tema.TOKEN["teks-mati"] if is_disabled else ("#ffffff" if is_hover else tema.TOKEN["teks-kedua"]))

        if self.jenis_ikon and not self.teks:
            lukis_ikon_vektor(p, self.jenis_ikon, w / 2.0, (h / 2.0) + y_offset, warna, sz=14)
        elif self.jenis_ikon and self.teks:
            lukis_ikon_vektor(p, self.jenis_ikon, 14, (h / 2.0) + y_offset, warna, sz=13)
            p.setFont(self.font())
            p.setPen(warna)
            p.drawText(QRect(26, y_offset, w - 30, h), Qt.AlignVCenter | Qt.AlignLeft, self.teks)
        else:
            p.setFont(self.font())
            p.setPen(warna)
            p.drawText(QRect(0, y_offset, w, h), Qt.AlignCenter, self.teks)

        if self.hasFocus():
            _lukis_cincin_fokus(p, rect, 6)


class TombolAlatAdobe(QPushButton):
    """Tombol rel vertikal Adobe yang bersih tanpa garis tepi kotak saat diam."""

    def __init__(self, jenis_ikon, tip="", parent=None):
        super().__init__(parent)
        self.jenis_ikon = jenis_ikon
        self.setCheckable(True)
        self.setFixedSize(36, 36)
        self.setToolTip(tip)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        is_checked = self.isChecked()
        is_hover = self.underMouse()
        is_pressed = self.isDown()

        rect_btn = QRectF(2, 2, self.width() - 4, self.height() - 4)

        if is_checked:
            painter.setBrush(QColor(20, 115, 230, 40))
            painter.setPen(QPen(QColor(tema.TOKEN["aksen"]), 1))
            painter.drawRoundedRect(rect_btn, 7, 7)

            painter.setBrush(QColor(tema.TOKEN["aksen"]))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(2, 10, 3, self.height() - 20), 1.5, 1.5)
        elif is_pressed:
            painter.setBrush(QColor(255, 255, 255, 20))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect_btn, 7, 7)
        elif is_hover:
            painter.setBrush(QColor(255, 255, 255, 16))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect_btn, 7, 7)
        else:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(Qt.NoPen)

        warna_ikon = QColor("#ffffff" if is_checked or is_hover else tema.TOKEN["teks-kedua"])
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        lukis_ikon_vektor(painter, self.jenis_ikon, cx, cy, warna_ikon, sz=15)

        if self.hasFocus():
            _lukis_cincin_fokus(painter, rect_btn, 6)


class KotakDimensiTerpadu(QFrame):
    """Display dimensi HUD minimalis dan bersih tanpa border kotak kaku."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 5px;
            }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(6)

        self.lbl_teks = QLabel("Belum ada seleksi")
        self.lbl_teks.setStyleSheet(f"color: {tema.TOKEN['teks-utama']}; font-weight: 600; font-size: 11px;")
        lay.addWidget(self.lbl_teks)

        self.lbl_rasio = QLabel("-")
        self.lbl_rasio.setStyleSheet(f"""
            background-color: rgba(20, 115, 230, 0.20);
            color: {tema.TOKEN['aksen-atas']};
            font-weight: 700;
            font-size: 10px;
            padding: 1px 6px;
            border-radius: 3px;
            border: none;
        """)
        self.lbl_rasio.setVisible(False)
        lay.addWidget(self.lbl_rasio)
        self.set_dimensi(0, 0)

    def set_dimensi(self, w, h):
        if w > 0 and h > 0:
            self.lbl_teks.setStyleSheet(f"color: {tema.TOKEN['teks-utama']}; font-weight: 600; font-size: 11px;")
            self.lbl_teks.setText(f"{w} × {h} px")
            self.lbl_rasio.setVisible(True)
            gcd = math.gcd(w, h)
            rw = w // gcd
            rh = h // gcd
            if rw <= 16 and rh <= 16:
                self.lbl_rasio.setText(f"{rw}:{rh}")
            else:
                self.lbl_rasio.setText(f"{w/h:.2f}")
        else:
            self.lbl_teks.setStyleSheet(f"color: {tema.TOKEN['teks-redup']}; font-weight: 500; font-size: 11px;")
            self.lbl_teks.setText("Belum ada seleksi")
            self.lbl_rasio.setVisible(False)


class SegmenPilihanAdobe(QFrame):
    """Grup segmen horizontal kapsul halus tanpa border kotak bertumpuk."""

    dipilih = Signal(int, str)

    def __init__(self, daftar_opsi, terpilih=0, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.daftar_opsi = daftar_opsi
        self.indeks_aktif = terpilih
        self.tombol_list = []

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.32);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 13px;
            }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(1)

        for i, opt in enumerate(daftar_opsi):
            btn = QPushButton(opt)
            btn.setFixedHeight(22)
            btn.setCheckable(True)
            btn.setChecked(i == terpilih)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._klik(idx))
            self._update_style(btn, i == terpilih)
            lay.addWidget(btn)
            self.tombol_list.append(btn)

    def _klik(self, idx):
        self.set_aktif(idx)
        self.dipilih.emit(idx, self.daftar_opsi[idx])

    def set_aktif(self, idx):
        """Menyorot opsi aktif tanpa memancarkan sinyal (untuk sinkronisasi zoom)."""
        self.indeks_aktif = idx
        for i, btn in enumerate(self.tombol_list):
            btn.setChecked(i == idx)
            self._update_style(btn, i == idx)

    def _update_style(self, btn, aktif):
        if aktif:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {tema.TOKEN['aksen-atas']}, stop:1 {tema.TOKEN['aksen-bawah']});
                    color: #ffffff;
                    border: none;
                    border-radius: 11px;
                    padding: 0px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:disabled {{
                    background: rgba(255, 255, 255, 0.04);
                    color: {tema.TOKEN['teks-mati']};
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {tema.TOKEN['teks-kedua']};
                    border: none;
                    border-radius: 11px;
                    padding: 0px 8px;
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #ffffff;
                }}
                QPushButton:disabled {{
                    background: transparent;
                    color: {tema.TOKEN['teks-mati']};
                }}
            """)

    def set_indeks(self, idx):
        if 0 <= idx < len(self.tombol_list):
            self._klik(idx)


class ChevronAdobe(QWidget):
    """Indikator lipat segitiga vektor presisi ala Adobe."""

    def __init__(self, terbuka=True, parent=None):
        super().__init__(parent)
        self.terbuka = terbuka
        self.setFixedSize(10, 10)

    def set_terbuka(self, terbuka):
        self.terbuka = terbuka
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setBrush(QColor(tema.TOKEN["teks-redup"]))
        p.setPen(Qt.NoPen)
        path = QPainterPath()
        if self.terbuka:
            path.moveTo(2, 3)
            path.lineTo(8, 3)
            path.lineTo(5, 7)
        else:
            path.moveTo(3, 2)
            path.lineTo(7, 5)
            path.lineTo(3, 8)
        path.closeSubpath()
        p.drawPath(path)


class PanelAccordionAdobe(QFrame):
    """Bagian modul inspektur clean design yang menyatu mulus tanpa kotak pembatas bertumpuk."""

    def __init__(self, judul, terbuka=True, parent=None):
        super().__init__(parent)
        self.terbuka = terbuka
        self.setStyleSheet(f"""
            PanelAccordionAdobe {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {tema.TOKEN['garis']};
            }}
        """)
        self.lay_induk = QVBoxLayout(self)
        self.lay_induk.setContentsMargins(14, 12, 14, 14)
        self.lay_induk.setSpacing(8)

        # Header bar
        self.btn_header = QPushButton()
        self.btn_header.setFixedHeight(24)
        self.btn_header.setCursor(Qt.PointingHandCursor)
        self.btn_header.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                text-align: left;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 4%);
                border-radius: 4px;
            }
        """)
        h_lay = QHBoxLayout(self.btn_header)
        h_lay.setContentsMargins(2, 0, 2, 0)
        h_lay.setSpacing(8)

        self.chevron = ChevronAdobe(self.terbuka)
        h_lay.addWidget(self.chevron)

        self.lbl_judul = QLabel(judul.upper())
        self.lbl_judul.setStyleSheet(f"""
            color: {tema.TOKEN['teks-kedua']};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.8px;
        """)
        h_lay.addWidget(self.lbl_judul)
        h_lay.addStretch(1)

        self.btn_header.clicked.connect(self._toggle)
        self.lay_induk.addWidget(self.btn_header)

        # Kontainer Konten
        self.konten = QWidget()
        self.lay_konten = QVBoxLayout(self.konten)
        self.lay_konten.setContentsMargins(0, 2, 0, 0)
        self.lay_konten.setSpacing(8)
        self.lay_induk.addWidget(self.konten)

        if not self.terbuka:
            self.konten.hide()

    def _toggle(self):
        self.terbuka = not self.terbuka
        self.chevron.set_terbuka(self.terbuka)
        self.konten.setVisible(self.terbuka)

    def tambah_widget(self, w):
        self.lay_konten.addWidget(w)

    def tambah_layout(self, lay):
        self.lay_konten.addLayout(lay)


class LencanaStatus(QFrame):
    """Lencana status perangkat dengan lampu indikator LED halus dan latar minimalis."""

    def __init__(self, teks="Mencari HP...", status="warn", parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 13px;
            }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(6)

        self.dot = QLabel("●")
        self.lbl = QLabel(teks)
        self.lbl.setStyleSheet(f"font-size: 11px; font-weight: 500; color: {tema.TOKEN['teks-utama']};")
        lay.addWidget(self.dot)
        lay.addWidget(self.lbl)
        self.set_status(teks, status)

    def set_status(self, teks, status="ok"):
        self.lbl.setText(teks)
        warna = tema.TOKEN["status-ok"]
        if status == "warn":
            warna = tema.TOKEN["status-warn"]
        elif status == "err":
            warna = tema.TOKEN["status-err"]
        self.dot.setStyleSheet(f"font-size: 10px; color: {warna};")


class KartuRiwayatItem(QWidget):
    """Item visual galeri riwayat sesi bersih dan rapi."""

    def __init__(self, nama, jalur, parent=None):
        super().__init__(parent)
        self.jalur = jalur
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(10)

        # Thumbnail tanpa border kaku
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(36, 48)
        self.lbl_thumb.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.04);
            border-radius: 4px;
        """)
        self.lbl_thumb.setScaledContents(True)

        dimensi = "Foto tersimpan"
        if jalur:
            pix = QPixmap(jalur)
            if not pix.isNull():
                self.lbl_thumb.setPixmap(pix.scaled(36, 48, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                dimensi = f"{pix.width()} × {pix.height()} px"

        lay.addWidget(self.lbl_thumb)

        # Info teks
        lay_info = QVBoxLayout()
        lay_info.setContentsMargins(0, 2, 0, 2)
        lay_info.setSpacing(2)

        lbl_nama = QLabel(nama)
        lbl_nama.setStyleSheet(f"font-weight: 600; font-size: 11px; color: {tema.TOKEN['teks-utama']};")
        lay_info.addWidget(lbl_nama)

        lbl_dim = QLabel(dimensi)
        lbl_dim.setStyleSheet(f"font-size: 10px; color: {tema.TOKEN['teks-redup']};")
        lay_info.addWidget(lbl_dim)

        lay.addLayout(lay_info, 1)


class NotifikasiToast(QFrame):
    """Notifikasi mengambang (toast) halus di atas kanvas dengan animasi pudar halus."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(20, 20, 20, 94%);
                border: 1px solid {tema.TOKEN['aksen']};
                border-radius: 17px;
                padding: 0px 14px;
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(8)

        self.lbl_icon = QLabel("✓")
        self.lbl_icon.setStyleSheet(f"color: {tema.TOKEN['status-ok']}; font-weight: 800; font-size: 12px;")
        lay.addWidget(self.lbl_icon)

        self.lbl_pesan = QLabel("Tersimpan")
        self.lbl_pesan.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 11px;")
        lay.addWidget(self.lbl_pesan)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.hide()

    def tampil(self, pesan, sukses=True):
        self.lbl_icon.setText("✓" if sukses else "✕")
        self.lbl_icon.setStyleSheet(f"color: {tema.TOKEN['status-ok'] if sukses else tema.TOKEN['status-err']}; font-weight: 800;")
        self.lbl_pesan.setText(pesan)
        self.adjustSize()

        if self.parent():
            pw = self.parent().width()
            ph = self.parent().height()
            self.move(pw - self.width() - 20, ph - self.height() - 20)
        self.show()
        self.raise_()
        self.timer.start(3500)
