"""Manajemen lokasi dan direktori berkas Phone Capture Studio."""
import os
import sys
import tempfile


def akar():
    """Mengembalikan direktori utama proyek/aplikasi."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # app/engine/lokasi.py -> naik 2 tingkat ke akar
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def folder_hasil_induk():
    """Folder utama penampung seluruh hasil tangkapan."""
    p = os.path.join(akar(), "hasil")
    os.makedirs(p, exist_ok=True)
    return p


def folder_hasil():
    """Folder penyimpanan foto yang sudah dipotong (crop)."""
    p = os.path.join(folder_hasil_induk(), "foto")
    # Dukungan kompatibilitas lama bila foto_absensi masih ada
    legacy = os.path.join(akar(), "foto_absensi")
    if os.path.isdir(legacy) and not os.path.exists(p):
        return legacy
    os.makedirs(p, exist_ok=True)
    return p


def folder_layar_penuh():
    """Folder tangkapan layar penuh mentah."""
    p = os.path.join(folder_hasil_induk(), "layar")
    legacy = os.path.join(akar(), "layar_penuh")
    if os.path.isdir(legacy) and not os.path.exists(p):
        return legacy
    os.makedirs(p, exist_ok=True)
    return p


def folder_layar_hd():
    """Folder hasil upscale 2x Lanczos."""
    p = os.path.join(folder_hasil_induk(), "hd")
    legacy = os.path.join(akar(), "layar_penuh_hd")
    if os.path.isdir(legacy) and not os.path.exists(p):
        return legacy
    os.makedirs(p, exist_ok=True)
    return p


def folder_layar_asli():
    """Folder cadangan layar asli sebelum dipotong."""
    p = os.path.join(folder_hasil_induk(), "asli")
    legacy = os.path.join(akar(), "layar_penuh_asli")
    if os.path.isdir(legacy) and not os.path.exists(p):
        return legacy
    os.makedirs(p, exist_ok=True)
    return p


def cari_adb():
    """Mencari binary adb.exe di folder lokal, SDK, atau emulator."""
    kandidat = [
        os.path.join(akar(), "adb", "adb.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        r"C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe",
        r"D:\LDPlayer\LDPlayer9\adb.exe",
    ]
    for k in kandidat:
        if os.path.isfile(k):
            return k
    import shutil
    di_path = shutil.which("adb.exe") or shutil.which("adb")
    if di_path:
        return di_path
    return None


def berkas_sementara(suffix=".png"):
    return os.path.join(tempfile.gettempdir(), f"pcs_temp_{os.getpid()}_{id(suffix)}{suffix}")
