"""Pemrosesan citra digital, pemotongan presisi, dan upscaling Lanczos."""
import datetime
import os
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from . import lokasi


def potong_koordinat(img, x, y, w, h):
    """Memotong gambar berdasarkan koordinat x, y, w, h asli."""
    if w <= 10 or h <= 10:
        return None
    # Pastikan koordinat dalam batas citra
    img_w, img_h = img.size
    x0 = max(0, min(img_w - 1, x))
    y0 = max(0, min(img_h - 1, y))
    x1 = max(0, min(img_w, x0 + w))
    y1 = max(0, min(img_h, y0 + h))
    if x1 <= x0 or y1 <= y0:
        return None
    return img.crop((x0, y0, x1, y1))


def proses_hd_lanczos(img):
    """Upscale 2x menggunakan interpolasi sinc Lanczos + penajaman optik.
    Murni pemrosesan citra, tanpa AI generatif sehingga wajah tetap otentik.
    """
    rgb = img.convert("RGB")
    lebar_baru = rgb.width * 2
    tinggi_baru = rgb.height * 2
    besar = rgb.resize((lebar_baru, tinggi_baru), Image.LANCZOS)
    tajam = besar.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
    hasil = ImageEnhance.Contrast(tajam).enhance(1.03)
    return hasil


def belum_dipotong(img):
    """True bila gambar masih berupa layar penampil utuh (status bar terang + bilah gelap di atas foto)."""
    a = np.asarray(img.convert("RGB"))
    h = a.shape[0]
    if h < 1000:
        return False
    atas = a[: int(h * 0.037)].mean()
    pita = a[int(h * 0.040): int(h * 0.105)].mean()
    return atas > 200 and pita < 50


def deteksi_kotak_foto(img):
    """Mendeteksi batas foto pada tangkapan layar penampil (membuang status bar & tombol)."""
    a = np.asarray(img.convert("RGB")).astype(int)
    h, w, _ = a.shape
    if h < 400:
        return 0, 0, w, h

    bg = a[int(h * 0.12), 5]  # sampel latar penampil
    # batas bawah = awal panel kontrol bawah
    bottom = h
    for y in range(int(h * 0.6), h):
        if a[y].min() > 225:
            bottom = y
            break
    top = int(h * 0.10)
    m = np.abs(a[top:bottom] - bg).max(axis=2) > 14
    rows = m.mean(axis=1) > 0.02

    best = (0, 0)
    st = None
    for i, r in enumerate(list(rows) + [False]):
        if r and st is None:
            st = i
        elif not r and st is not None:
            if i - st > best[1] - best[0]:
                best = (st, i)
            st = None

    y0, y1 = top + best[0], top + best[1]
    if y1 - y0 < 100:
        return 0, 0, w, h

    cols = np.where(np.abs(a[y0:y1] - bg).max(axis=2).__gt__(14).mean(axis=0) > 0.02)[0]
    if len(cols) == 0:
        return 0, 0, w, h

    x0 = int(cols.min())
    x1 = int(cols.max()) + 1
    return x0, y0, (x1 - x0), (y1 - y0)


def simpan_hasil(img_crop, buat_hd=False):
    """Menyimpan potongan foto ke hasil/foto (dan versi 2x ke hasil/hd bila diminta)."""
    folder = lokasi.folder_hasil()
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    nama_file = f"foto_{stamp}.png"
    jalur_file = os.path.join(folder, nama_file)

    img_crop.save(jalur_file, format="PNG", optimize=True)

    jalur_hd = None
    if buat_hd:
        folder_hd = lokasi.folder_layar_hd()
        nama_hd = f"hd_{stamp}.png"
        jalur_hd = os.path.join(folder_hd, nama_hd)
        img_hd = proses_hd_lanczos(img_crop)
        img_hd.save(jalur_hd, format="PNG", optimize=True)

    return {
        "nama": nama_file,
        "jalur": jalur_file,
        "jalur_hd": jalur_hd,
        "w": img_crop.width,
        "h": img_crop.height,
        "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
    }


def simpan_layar_penuh(img_full):
    """Menyimpan seluruh layar mentah ke hasil/layar."""
    folder = lokasi.folder_layar_penuh()
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    nama_file = f"layar_{stamp}.png"
    jalur_file = os.path.join(folder, nama_file)
    img_full.save(jalur_file, format="PNG", optimize=True)
    return {
        "nama": nama_file,
        "jalur": jalur_file,
        "w": img_full.width,
        "h": img_full.height,
        "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
    }
