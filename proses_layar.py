"""Pemrosesan batch tangkapan layar di hasil/layar/ (buang frame penampil) lalu buat versi HD.

Perintah:
    python proses_layar.py detect   -> Tampilkan batas potong tiap file
    python proses_layar.py crop     -> Potong gambar di hasil/layar/ secara massal
    python proses_layar.py hd       -> Buat versi HD (2x Lanczos) di hasil/hd/
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "hasil" / "layar"
if not SRC.exists():
    SRC = ROOT / "layar_penuh"
HD = ROOT / "hasil" / "hd"
if not HD.exists():
    HD = ROOT / "layar_penuh_hd"

sys.path.insert(0, str(ROOT / "app"))
from engine.processor import belum_dipotong, deteksi_kotak_foto, proses_hd_lanczos
from PIL import Image


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "detect"
    files = sorted(SRC.glob("*.png"))
    if not files:
        print(f"Tidak ada file PNG di {SRC}")
        sys.exit(0)

    if mode == "hd":
        HD.mkdir(parents=True, exist_ok=True)

    for f in files:
        img = Image.open(f)
        img.load()
        if mode in ("detect", "crop"):
            if not belum_dipotong(img):
                print(f.name, img.size, "-> dilewati (sudah dipotong)")
                continue
            x, y, w, h = deteksi_kotak_foto(img)
            box = (x, y, x + w, y + h)
            print(f.name, img.size, "-> kotak:", box, f"ukuran: {w}x{h}")
            if mode == "crop":
                img.crop(box).save(f, optimize=True)
        elif mode == "hd":
            out = HD / f.name.replace("layar_", "hd_")
            proses_hd_lanczos(img).save(out, optimize=True)
            print(out.name, img.size, "->", (img.width * 2, img.height * 2))
