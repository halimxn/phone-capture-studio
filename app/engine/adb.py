"""Interaksi ADB (Android Debug Bridge) untuk tangkapan layar dan kontrol display."""
import os
import re
import subprocess
from . import lokasi

STARTUPINFO = None
if os.name == "nt":
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    STARTUPINFO.wShowWindow = 0  # SW_HIDE


def _jalankan(args, timeout=10):
    adb = lokasi.cari_adb()
    if not adb:
        return None, "ADB tidak ditemukan"
    cmd = [adb] + args
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            startupinfo=STARTUPINFO,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        return res.stdout.strip(), None
    except Exception as e:
        return None, str(e)


def _jalankan_biner(args, timeout=15):
    adb = lokasi.cari_adb()
    if not adb:
        return None, "ADB tidak ditemukan"
    cmd = [adb] + args
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            startupinfo=STARTUPINFO,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        return res.stdout, None
    except Exception as e:
        return None, str(e)


def cek_perangkat():
    """Mengembalikan (serial, status, pesan).
    status: 'device', 'unauthorized', 'offline', 'tidak_ada', 'tidak_ada_adb'
    """
    adb = lokasi.cari_adb()
    if not adb:
        return None, "tidak_ada_adb", "Binary adb.exe tidak ditemukan"

    out, err = _jalankan(["devices"])
    if err or not out:
        return None, "tidak_ada", "Gagal menjalankan adb"

    for line in out.splitlines():
        line = line.strip()
        m = re.match(r"^(\S+)\s+(device|unauthorized|offline)$", line)
        if m:
            serial, st = m.groups()
            if serial.startswith("emulator-") or serial.startswith("127.0.0.1"):
                continue
            if st == "device":
                model_nama = model_perangkat(serial)
                label = f"{model_nama} ({serial})" if model_nama else f"Terhubung ({serial})"
                return serial, "device", label
            elif st == "unauthorized":
                return serial, "unauthorized", "Otorisasi dibutuhkan: ketuk Izinkan di HP"
            elif st == "offline":
                return serial, "offline", "Perangkat offline"

    return None, "tidak_ada", "Tidak ada HP terhubung via USB"


def model_perangkat(serial):
    """Membaca merek & model perangkat Android via getprop."""
    if not serial:
        return None
    model, _ = _jalankan(["-s", serial, "shell", "getprop", "ro.product.model"])
    brand, _ = _jalankan(["-s", serial, "shell", "getprop", "ro.product.brand"])
    brand_str = brand.capitalize() if brand else ""
    model_str = model if model else ""
    if brand_str and model_str:
        if not model_str.lower().startswith(brand_str.lower()):
            return f"{brand_str} {model_str}"
        return model_str
    return model_str or serial


def info_layar(serial):
    """Membaca ukuran fisik & override layar."""
    if not serial:
        return None
    out_s, _ = _jalankan(["-s", serial, "shell", "wm", "size"])
    out_d, _ = _jalankan(["-s", serial, "shell", "wm", "density"])
    if not out_s or not out_d:
        return None

    info = {"pw": 0, "ph": 0, "pd": 0, "w": 0, "h": 0, "d": 0, "override": False}

    m_pw = re.search(r"Physical size:\s*(\d+)x(\d+)", out_s)
    if m_pw:
        info["pw"] = int(m_pw.group(1))
        info["ph"] = int(m_pw.group(2))
    info["w"] = info["pw"]
    info["h"] = info["ph"]

    m_ow = re.search(r"Override size:\s*(\d+)x(\d+)", out_s)
    if m_ow:
        info["w"] = int(m_ow.group(1))
        info["h"] = int(m_ow.group(2))
        info["override"] = True

    m_pd = re.search(r"Physical density:\s*(\d+)", out_d)
    if m_pd:
        info["pd"] = int(m_pd.group(1))
    info["d"] = info["pd"]

    m_od = re.search(r"Override density:\s*(\d+)", out_d)
    if m_od:
        info["d"] = int(m_od.group(1))
        info["override"] = True

    if info["pw"] <= 0 or info["pd"] <= 0:
        return None

    # Hitung persentase tampilan efektif
    try:
        skala = (info["d"] / info["pd"]) / (info["w"] / info["pw"])
        info["zoom_tampilan"] = int(round(skala * 100))
    except Exception:
        info["zoom_tampilan"] = 100

    return info


def terapkan_hd(serial, faktor_zoom=1.0):
    """Menaikkan resolusi layar HP hingga 2x (batas 4096px) dengan zoom tampilan."""
    info = info_layar(serial)
    if not info:
        return False, "Tidak dapat membaca informasi layar HP"

    panjang = max(info["pw"], info["ph"])
    k = min(2.0, 4096.0 / panjang)
    if k < 1.0:
        k = 1.0

    nw = int(round(info["pw"] * k / 2.0) * 2)
    nh = int(round(info["ph"] * k / 2.0) * 2)
    nd = int(round(info["pd"] * k * faktor_zoom))

    _jalankan(["-s", serial, "shell", "wm", "size", f"{nw}x{nh}"])
    _jalankan(["-s", serial, "shell", "wm", "density", str(nd)])
    return True, f"Mode HD diterapkan: {nw}x{nh} ({nd} dpi)"


def reset_layar(serial):
    """Mengembalikan resolusi dan kepadatan layar HP ke normal."""
    if not serial:
        return False, "Perangkat tidak valid"
    _jalankan(["-s", serial, "shell", "wm", "size", "reset"])
    _jalankan(["-s", serial, "shell", "wm", "density", "reset"])
    return True, "Resolusi layar dikembalikan ke default"


def ambil_tangkapan_layar(serial):
    """Mengambil tangkapan layar langsung dalam bentuk bytes PNG."""
    if not serial:
        return None, "Perangkat tidak terhubung"

    # Bangunkan layar bila sedang mati
    _jalankan(["-s", serial, "shell", "input", "keyevent", "KEYCODE_WAKEUP"])

    # Jalur cepat: exec-out screencap -p
    raw, err = _jalankan_biner(["-s", serial, "exec-out", "screencap", "-p"])
    if raw and len(raw) > 1000 and raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return raw, None

    # Jalur cadangan: pull file sementara
    tmp_hp = "/sdcard/_pcs_frame.png"
    tmp_pc = lokasi.berkas_sementara(".png")
    _jalankan(["-s", serial, "shell", "screencap", "-p", tmp_hp])
    _jalankan(["-s", serial, "pull", tmp_hp, tmp_pc])
    _jalankan(["-s", serial, "shell", "rm", tmp_hp])

    if os.path.isfile(tmp_pc):
        try:
            with open(tmp_pc, "rb") as f:
                data = f.read()
            os.remove(tmp_pc)
            if data and data.startswith(b"\x89PNG\r\n\x1a\n"):
                return data, None
        except Exception as e:
            return None, str(e)

    return None, "Gagal mengambil tangkapan layar dari HP"
