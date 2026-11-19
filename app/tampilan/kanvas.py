"""Kanvas interaktif Adobe: visualisasi viewport ponsel, marching ants animasi, dan 8 handle presisi."""
import math
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, Signal, QTimer
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
from PySide6.QtWidgets import QFrame, QPushButton, QScrollArea, QWidget
from . import komponen, tema


class KanvasArea(QWidget):
    """Area render gambar dengan efek kedalaman bayangan, marching ants, dan manipulasi seleksi 8 arah."""

    seleksi_berubah = Signal(int, int, int, int)
    zoom_berubah = Signal(int)
    minta_ambil_layar = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap_asli = None
        self.skala = 1.0
        self.mode_pas = True

        # State seleksi (dalam PIKSEL ASLI GAMBAR)
        self.has_sel = False
        self.sel_x = 0
        self.sel_y = 0
        self.sel_w = 0
        self.sel_h = 0

        # Rasio aspek terkunci
        self.rasio_kunci = None

        # State interaksi
        self.alat_aktif = "seleksi"  # 'seleksi', 'geser', 'zoom'
        self.drag_mode = None        # 'create', 'move', 'nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'
        self.drag_start_client = QPoint()
        self.sel_start_box = (0, 0, 0, 0)

        # Pan
        self.panning = False
        self.pan_start = QPoint()

        # Animasi Marching Ants
        self.dash_offset = 0
        self.timer_ants = QTimer(self)
        self.timer_ants.timeout.connect(self._langkah_ants)
        self.timer_ants.start(120)

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def _langkah_ants(self):
        if self.has_sel:
            self.dash_offset = (self.dash_offset + 1) % 8
            self.update()

    def set_gambar(self, pixmap):
        self.pixmap_asli = pixmap
        self.has_sel = False
        self.seleksi_berubah.emit(0, 0, 0, 0)
        self.sesuaikan_ukuran()
        self.update()

    def set_rasio_kunci(self, rasio):
        self.rasio_kunci = rasio
        if self.has_sel and self.rasio_kunci and self.sel_w > 0:
            h_baru = int(round(self.sel_w / self.rasio_kunci))
            self.set_seleksi_piksel(self.sel_x, self.sel_y, self.sel_w, h_baru)

    def sesuaikan_ukuran(self):
        if not self.pixmap_asli:
            p = self.parent()
            if p and p.width() > 50 and p.height() > 50:
                self.resize(p.size())
            else:
                self.resize(800, 600)
            return

        if self.mode_pas:
            p = self.parent()
            if p and p.width() > 50 and p.height() > 50:
                vw = p.width() - 40
                vh = p.height() - 40
                sx = vw / self.pixmap_asli.width()
                sy = vh / self.pixmap_asli.height()
                self.skala = min(sx, sy, 1.0)
            else:
                self.skala = 0.5

        w = max(100, int(round(self.pixmap_asli.width() * self.skala)))
        h = max(100, int(round(self.pixmap_asli.height() * self.skala)))
        self.resize(w, h)
        self.zoom_berubah.emit(int(round(self.skala * 100)))

    def atur_zoom(self, skala_desimal):
        if skala_desimal <= 0:
            self.mode_pas = True
        else:
            self.mode_pas = False
            self.skala = max(0.1, min(5.0, skala_desimal))
        self.sesuaikan_ukuran()
        self.update()

    def hapus_seleksi(self):
        self.has_sel = False
        self.seleksi_berubah.emit(0, 0, 0, 0)
        self.update()

    def set_seleksi_piksel(self, x, y, w, h):
        if not self.pixmap_asli:
            return
        iw = self.pixmap_asli.width()
        ih = self.pixmap_asli.height()

        x = max(0, min(iw - 5, x))
        y = max(0, min(ih - 5, y))
        w = max(0, min(iw - x, w))
        h = max(0, min(ih - y, h))

        self.sel_x = x
        self.sel_y = y
        self.sel_w = w
        self.sel_h = h
        self.has_sel = (w > 5 and h > 5)
        self.seleksi_berubah.emit(self.sel_x, self.sel_y, self.sel_w, self.sel_h)
        self.update()

    def _client_ke_img(self, pt):
        if not self.pixmap_asli or self.skala <= 0:
            return 0, 0
        ix = int(round(pt.x() / self.skala))
        iy = int(round(pt.y() / self.skala))
        ix = max(0, min(self.pixmap_asli.width(), ix))
        iy = max(0, min(self.pixmap_asli.height(), iy))
        return ix, iy

    def _img_ke_client(self, x, y, w, h):
        cx = int(round(x * self.skala))
        cy = int(round(y * self.skala))
        cw = int(round(w * self.skala))
        ch = int(round(h * self.skala))
        return cx, cy, cw, ch

    def _dapatkan_handle_dibawah_mouse(self, pt):
        if not self.has_sel:
            return None

        cx, cy, cw, ch = self._img_ke_client(self.sel_x, self.sel_y, self.sel_w, self.sel_h)
        r = 6

        handles = {
            "nw": QRect(cx - r, cy - r, r * 2, r * 2),
            "ne": QRect(cx + cw - r, cy - r, r * 2, r * 2),
            "se": QRect(cx + cw - r, cy + ch - r, r * 2, r * 2),
            "sw": QRect(cx - r, cy + ch - r, r * 2, r * 2),
            "n": QRect(cx + cw // 2 - r, cy - r, r * 2, r * 2),
            "s": QRect(cx + cw // 2 - r, cy + ch - r, r * 2, r * 2),
            "w": QRect(cx - r, cy + ch // 2 - r, r * 2, r * 2),
            "e": QRect(cx + cw - r, cy + ch // 2 - r, r * 2, r * 2),
        }

        for k, rect in handles.items():
            if rect.contains(pt):
                return k

        box_rect = QRect(cx, cy, cw, ch)
        if box_rect.contains(pt):
            return "move"

        return None

    def _cta_rect(self):
        cx = self.width() // 2
        cy = self.height() // 2
        btn_w = 270
        btn_h = 42
        return QRect(cx - btn_w // 2, cy + 70, btn_w, btn_h)

    def mousePressEvent(self, event):
        if not self.pixmap_asli:
            pos = event.position().toPoint()
            if self._cta_rect().contains(pos):
                self.minta_ambil_layar.emit()
            return

        if event.button() == Qt.RightButton or self.alat_aktif == "geser":
            self.panning = True
            self.pan_start = event.globalPosition().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            if self.alat_aktif == "zoom":
                self.mode_pas = False
                self.skala = min(4.0, self.skala * 1.25)
                self.sesuaikan_ukuran()
                self.update()
                return

            pos = event.position().toPoint()
            mode = self._dapatkan_handle_dibawah_mouse(pos)

            self.drag_start_client = pos
            self.sel_start_box = (self.sel_x, self.sel_y, self.sel_w, self.sel_h)

            if mode:
                self.drag_mode = mode
            else:
                self.drag_mode = "create"
                ix, iy = self._client_ke_img(pos)
                self.set_seleksi_piksel(ix, iy, 0, 0)

            event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()

        if self.panning:
            cur = event.globalPosition().toPoint()
            delta = cur - self.pan_start
            self.pan_start = cur
            sa = self.parentWidget()
            if isinstance(sa, QScrollArea):
                sa.horizontalScrollBar().setValue(sa.horizontalScrollBar().value() - delta.x())
                sa.verticalScrollBar().setValue(sa.verticalScrollBar().value() - delta.y())
            elif sa and isinstance(sa.parentWidget(), QScrollArea):
                parent_sa = sa.parentWidget()
                parent_sa.horizontalScrollBar().setValue(parent_sa.horizontalScrollBar().value() - delta.x())
                parent_sa.verticalScrollBar().setValue(parent_sa.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        if not self.drag_mode:
            if not self.pixmap_asli:
                self.setCursor(Qt.PointingHandCursor if self._cta_rect().contains(pos) else Qt.ArrowCursor)
                return

            if self.alat_aktif == "geser":
                self.setCursor(Qt.OpenHandCursor)
            elif self.alat_aktif == "zoom":
                self.setCursor(Qt.PointingHandCursor)
            else:
                handle = self._dapatkan_handle_dibawah_mouse(pos)
                if handle in ("nw", "se"):
                    self.setCursor(Qt.SizeFDiagCursor)
                elif handle in ("ne", "sw"):
                    self.setCursor(Qt.SizeBDiagCursor)
                elif handle in ("n", "s"):
                    self.setCursor(Qt.SizeVerCursor)
                elif handle in ("e", "w"):
                    self.setCursor(Qt.SizeHorCursor)
                elif handle == "move":
                    self.setCursor(Qt.SizeAllCursor)
                else:
                    self.setCursor(Qt.CrossCursor)

        if self.drag_mode:
            dx_px = int(round((pos.x() - self.drag_start_client.x()) / self.skala))
            dy_px = int(round((pos.y() - self.drag_start_client.y()) / self.skala))
            ox, oy, ow, oh = self.sel_start_box

            if self.drag_mode == "create":
                ix, iy = self._client_ke_img(pos)
                sx = min(ox, ix)
                sy = min(oy, iy)
                sw = abs(ix - ox)
                sh = abs(iy - oy)
                if self.rasio_kunci:
                    sh = int(round(sw / self.rasio_kunci))
                self.set_seleksi_piksel(sx, sy, sw, sh)
            elif self.drag_mode == "move":
                self.set_seleksi_piksel(ox + dx_px, oy + dy_px, ow, oh)
            elif self.drag_mode == "se":
                nw = max(10, ow + dx_px)
                nh = int(round(nw / self.rasio_kunci)) if self.rasio_kunci else max(10, oh + dy_px)
                self.set_seleksi_piksel(ox, oy, nw, nh)
            elif self.drag_mode == "e":
                nw = max(10, ow + dx_px)
                nh = int(round(nw / self.rasio_kunci)) if self.rasio_kunci else oh
                self.set_seleksi_piksel(ox, oy, nw, nh)
            elif self.drag_mode == "s":
                nh = max(10, oh + dy_px)
                nw = int(round(nh * self.rasio_kunci)) if self.rasio_kunci else ow
                self.set_seleksi_piksel(ox, oy, nw, nh)
            elif self.drag_mode == "nw":
                nw = max(10, ow - dx_px)
                nh = int(round(nw / self.rasio_kunci)) if self.rasio_kunci else max(10, oh - dy_px)
                self.set_seleksi_piksel(ox + (ow - nw), oy + (oh - nh), nw, nh)

            event.accept()

    def mouseReleaseEvent(self, event):
        if self.panning:
            self.panning = False
            self.setCursor(Qt.OpenHandCursor if self.alat_aktif == "geser" else Qt.CrossCursor)
            event.accept()
            return

        if self.drag_mode:
            self.drag_mode = None
            if self.sel_w < 8 or self.sel_h < 8:
                self.hapus_seleksi()
            event.accept()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            event.accept()
            delta = event.angleDelta().y()
            faktor = 1.15 if delta > 0 else (1.0 / 1.15)
            self.mode_pas = False
            self.skala = max(0.1, min(5.0, self.skala * faktor))
            self.sesuaikan_ukuran()
            self.update()
        else:
            event.ignore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # 1. Gambar Keadaan Kosong (Empty State) yang Ramah & Profesional
        if not self.pixmap_asli:
            painter.fillRect(self.rect(), QColor(tema.TOKEN["latar-kanvas"]))
            cx = self.width() // 2
            cy = self.height() // 2

            # Gambar Vektor Ponsel Minimalis
            pw = 64
            ph = 110
            px = cx - pw // 2
            py = cy - ph // 2 - 40

            painter.setPen(QPen(QColor(tema.TOKEN["garis"]), 2))
            painter.setBrush(QColor("#202020"))
            painter.drawRoundedRect(px, py, pw, ph, 10, 10)

            # Garis Layar Dalam
            painter.setPen(QPen(QColor(tema.TOKEN["garis-lembut"]), 1))
            painter.setBrush(QColor("#181818"))
            painter.drawRoundedRect(px + 4, py + 8, pw - 8, ph - 16, 4, 4)

            # Ikon Kamera / Lensa di tengah layar ponsel
            painter.setPen(QPen(QColor(tema.TOKEN["aksen"]), 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(cx, py + ph // 2), 10, 10)
            painter.drawEllipse(QPointF(cx, py + ph // 2), 4, 4)

            # Judul & Subteks
            painter.setPen(QColor(tema.TOKEN["teks-utama"]))
            font_judul = QFont(self.font())
            font_judul.setPixelSize(14)
            font_judul.setBold(True)
            painter.setFont(font_judul)
            painter.drawText(QRect(cx - 200, cy + 25, 400, 24), Qt.AlignCenter, "Siap Mengambil Layar Android")

            painter.setPen(QColor(tema.TOKEN["teks-redup"]))
            font_sub = QFont(self.font())
            font_sub.setPixelSize(11)
            painter.setFont(font_sub)
            painter.drawText(
                QRect(cx - 250, cy + 50, 500, 20),
                Qt.AlignCenter,
                "Sambungkan ponsel via USB (mode transfer file & aktifkan USB Debugging)",
            )

            # Tombol CTA Pusat Fluid & Tactile
            btn_rect = self._cta_rect()
            grad_btn = QLinearGradient(0, btn_rect.top(), 0, btn_rect.bottom())
            grad_btn.setColorAt(0, QColor(tema.TOKEN["aksen-atas"]))
            grad_btn.setColorAt(1, QColor(tema.TOKEN["aksen-bawah"]))

            painter.setPen(QPen(QColor(tema.TOKEN["aksen"]), 1))
            painter.setBrush(QBrush(grad_btn))
            painter.drawRoundedRect(btn_rect, 8, 8)

            # Specular highlight
            painter.setPen(QPen(QColor(255, 255, 255, 55), 1))
            painter.drawLine(btn_rect.left() + 8, btn_rect.top() + 1, btn_rect.right() - 8, btn_rect.top() + 1)

            # Ikon Kamera Vektor
            lukis_kamera = getattr(komponen, "lukis_ikon_vektor", None)
            if lukis_kamera:
                lukis_kamera(painter, "kamera", btn_rect.left() + 22, btn_rect.center().y(), QColor("#ffffff"), sz=16)

            # Teks CTA
            painter.setPen(QColor("#ffffff"))
            font_btn = QFont(self.font())
            font_btn.setPixelSize(12)
            font_btn.setBold(True)
            painter.setFont(font_btn)
            rect_txt = QRect(btn_rect.left() + 38, btn_rect.top(), btn_rect.width() - 86, btn_rect.height())
            painter.drawText(rect_txt, Qt.AlignVCenter | Qt.AlignLeft, "Ambil Layar Sekarang")

            # Kbd badge F5
            kbd_rect = QRect(btn_rect.right() - 44, btn_rect.center().y() - 10, 32, 20)
            painter.setBrush(QColor(0, 0, 0, 70))
            painter.setPen(QPen(QColor(255, 255, 255, 35), 1))
            painter.drawRoundedRect(kbd_rect, 4, 4)
            painter.setPen(QColor("#dceaff"))
            font_kbd = QFont(self.font())
            font_kbd.setPixelSize(10)
            font_kbd.setBold(True)
            painter.setFont(font_kbd)
            painter.drawText(kbd_rect, Qt.AlignCenter, "F5")

            # Petunjuk satu baris untuk langkah setelah layar dimuat
            painter.setPen(QColor(tema.TOKEN["teks-redup"]))
            font_info = QFont(self.font())
            font_info.setPixelSize(11)
            painter.setFont(font_info)
            painter.drawText(
                QRect(cx - 280, cy + 122, 560, 18),
                Qt.AlignCenter,
                "Setelah layar muncul, tarik kotak lalu tekan Enter. Tekan A untuk deteksi otomatis.",
            )
            return

        # 2. Gambar Screenshot Presisi
        target_rect = QRect(0, 0, self.width(), self.height())
        painter.drawPixmap(target_rect, self.pixmap_asli)

        # 3. Gambar Seleksi Kotak (Marquee)
        if self.has_sel and self.sel_w > 2 and self.sel_h > 2:
            cx, cy, cw, ch = self._img_ke_client(self.sel_x, self.sel_y, self.sel_w, self.sel_h)
            rect_sel = QRect(cx, cy, cw, ch)

            # Masking gelap di luar kotak seleksi
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 85))
            painter.drawRect(0, 0, self.width(), cy)
            painter.drawRect(0, cy + ch, self.width(), self.height() - (cy + ch))
            painter.drawRect(0, cy, cx, ch)
            painter.drawRect(cx + cw, cy, self.width() - (cx + cw), ch)

            # Latar transparan biru lembut
            painter.fillRect(rect_sel, QColor(20, 115, 230, 30))

            # Garis Marching Ants Ganda (Hitam padat di bawah, Putih putus-putus bergeser di atas)
            painter.setPen(QPen(QColor("#000000"), 1, Qt.SolidLine))
            painter.drawRect(rect_sel)

            pen_ants = QPen(QColor("#ffffff"), 1, Qt.CustomDashLine)
            pen_ants.setDashPattern([4, 4])
            pen_ants.setDashOffset(self.dash_offset)
            painter.setPen(pen_ants)
            painter.drawRect(rect_sel)

            # 8 Titik Pegangan Sudut & Sisi (Handles) dengan drop shadow mikro
            hs = 6
            half = hs // 2
            painter.setBrush(QColor("#ffffff"))
            painter.setPen(QPen(QColor("#000000"), 1))

            titik_handle = [
                (cx - half, cy - half),
                (cx + cw // 2 - half, cy - half),
                (cx + cw - half, cy - half),
                (cx + cw - half, cy + ch // 2 - half),
                (cx + cw - half, cy + ch - half),
                (cx + cw // 2 - half, cy + ch - half),
                (cx - half, cy + ch - half),
                (cx - half, cy + ch // 2 - half),
            ]
            for hx, hy in titik_handle:
                painter.drawRect(hx, hy, hs, hs)

            # Lencana Dimensi Terapung (HUD Badge)
            teks_dim = f"{self.sel_w} × {self.sel_h} px"
            teks_ratio = ""
            if self.sel_h > 0:
                gcd = math.gcd(self.sel_w, self.sel_h)
                rw = self.sel_w // gcd
                rh = self.sel_h // gcd
                if rw <= 16 and rh <= 16:
                    teks_ratio = f" ({rw}:{rh})"

            font_hud = QFont(self.font())
            font_hud.setPixelSize(10)
            font_hud.setBold(True)
            painter.setFont(font_hud)
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(teks_dim + teks_ratio) + 16
            th = fm.height() + 6

            bx = cx
            by = cy - th - 6
            if by < 6:
                by = cy + ch + 6

            # Latar Glass Gelap Badge
            painter.setBrush(QColor(24, 24, 24, 230))
            painter.setPen(QPen(QColor(tema.TOKEN["aksen"]), 1))
            painter.drawRoundedRect(bx, by, tw, th, 4, 4)

            # Teks Dimensi
            painter.setPen(QColor("#ffffff"))
            painter.drawText(QRect(bx, by, tw, th), Qt.AlignCenter, teks_dim + teks_ratio)


class KanvasAdobe(QScrollArea):
    """Kontainer QScrollArea terpusat dengan pasteboard gelap Adobe."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignCenter)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: {tema.TOKEN['latar-kanvas']};
                border: none;
            }}
        """)
        self.kanvas = KanvasArea(self)
        self.setWidget(self.kanvas)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.kanvas.mode_pas:
            self.kanvas.sesuaikan_ukuran()
