# Ambil foto yang sedang tampil di layar HP Android (via USB debugging),
# lalu potong otomatis hanya bagian fotonya dan simpan ke folder foto_absensi.
# Pakai: buka fotonya di HP, lalu jalankan:  powershell -ExecutionPolicy Bypass -File .\ambil_foto.ps1
param([string]$Src)   # opsional: potong file PNG yang sudah ada, tanpa screenshot baru

$adb = Join-Path $PSScriptRoot 'adb\adb.exe'
if (-not (Test-Path $adb)) { $adb = 'adb.exe' }
$ph = $null
if (-not $Src) {
    foreach ($l in (& $adb devices 2>$null)) { if ($l -match '^(\S+)\s+device$' -and $Matches[1] -notmatch '^emulator-') { $ph = $Matches[1]; break } }
    if (-not $ph) { throw "HP tidak terhubung / belum diizinkan. Colok USB lalu ketuk 'Izinkan' di HP." }
}
$out = Join-Path $PSScriptRoot 'foto_absensi'
New-Item -ItemType Directory -Force $out | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'

if (-not $Src) {
    & $adb -s $ph shell input keyevent KEYCODE_WAKEUP
    Start-Sleep -Milliseconds 500
    $Src = Join-Path $out "layar_$stamp.png"
    & $adb -s $ph shell screencap -p /sdcard/_ss_tmp.png
    & $adb -s $ph pull /sdcard/_ss_tmp.png $Src | Out-Null
    & $adb -s $ph shell rm /sdcard/_ss_tmp.png
}

Add-Type -AssemblyName System.Drawing
$img = New-Object System.Drawing.Bitmap $Src
$w = $img.Width; $h = $img.Height

# Baris "foto" = baris yang punya cukup piksel tidak gelap/tidak putih polos (bukan latar penampil).
function IsPhotoRow([int]$y) {
    $hits = 0
    for ($x = 0; $x -lt $w; $x += 24) {
        $c = $img.GetPixel($x, $y)
        $mx = [Math]::Max($c.R, [Math]::Max($c.G, $c.B)); $mn = [Math]::Min($c.R, [Math]::Min($c.G, $c.B))
        if ($mx -gt 40 -and -not ($mn -gt 245)) { $hits++ }
    }
    return ($hits -ge 10)
}

# Cari blok baris foto terpanjang (lewati bilah status, header, dan tombol bawah).
$best = @(0, 0); $start = -1
for ($y = 0; $y -lt $h; $y += 2) {
    if (IsPhotoRow $y) { if ($start -lt 0) { $start = $y } }
    elseif ($start -ge 0) { if (($y - $start) -gt ($best[1] - $best[0])) { $best = @($start, $y) }; $start = -1 }
}
if ($start -ge 0 -and (($h - $start) -gt ($best[1] - $best[0]))) { $best = @($start, $h) }
$top = $best[0]; $bot = $best[1]
if (($bot - $top) -lt 200) { $img.Dispose(); throw "Foto tidak terdeteksi di layar. Pastikan fotonya sedang terbuka." }

$rect = New-Object System.Drawing.Rectangle 0, $top, $w, ($bot - $top)
$crop = $img.Clone($rect, $img.PixelFormat)
$dest = Join-Path $out "foto_$stamp.png"
$crop.Save($dest, [System.Drawing.Imaging.ImageFormat]::Png)
$crop.Dispose(); $img.Dispose()
Write-Host ("Tersimpan: foto_absensi\{0}  ({1}x{2})" -f (Split-Path $dest -Leaf), $w, ($bot - $top))
