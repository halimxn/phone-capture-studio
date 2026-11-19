// PhoneCaptureStudio.exe di akar proyek: membuka aplikasi dari kode, sehingga perubahan langsung aktif tanpa proses kemas ulang yang lama.
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("Phone Capture Studio")]
[assembly: AssemblyProduct("Phone Capture Studio")]
[assembly: AssemblyCompany("Halim")]
[assembly: AssemblyCopyright("Copyright (c) 2026")]
[assembly: AssemblyVersion("@VERSI@.0")]
[assembly: AssemblyFileVersion("@VERSI@.0")]

static class Peluncur
{
    [STAThread]
    static int Main()
    {
        string akar = AppDomain.CurrentDomain.BaseDirectory;
        string python = Path.Combine(akar, @".venv\Scripts\pythonw.exe");
        if (!File.Exists(python))
        {
            python = Path.Combine(akar, @".venv\Scripts\python.exe");
        }
        string utama = Path.Combine(akar, @"app\main.py");
        if (!File.Exists(python) || !File.Exists(utama))
        {
            MessageBox.Show("Lingkungan virtual Python (.venv) atau berkas app\\main.py belum siap.\n\n" +
                            "Jalankan di folder ini:\n" +
                            "uv venv .venv\n" +
                            "uv pip install PySide6 Pillow numpy",
                            "Phone Capture Studio", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }

        ProcessStartInfo info = new ProcessStartInfo(python, "\"" + utama + "\"");
        info.WorkingDirectory = akar;
        info.UseShellExecute = false;
        info.CreateNoWindow = true;
        try
        {
            Process.Start(info);
            return 0;
        }
        catch (Exception ex)
        {
            MessageBox.Show("Gagal menjalankan aplikasi:\n" + ex.Message,
                            "Phone Capture Studio", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
