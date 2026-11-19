# ============================================================
#  Phone Capture Studio  -  Ambil & potong foto dari layar HP Android
#  Lewat USB debugging (ADB). Tidak menyentuh server/akun.
#  Jalankan: klik dua kali "Jalankan Phone Capture Studio.cmd"
# ============================================================
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$Root   = $PSScriptRoot
$OutDir = Join-Path $Root 'foto_absensi'
$RawDir = Join-Path $Root 'layar_penuh'      # screenshot asli (tidak dipotong)
New-Item -ItemType Directory -Force $OutDir | Out-Null
New-Item -ItemType Directory -Force $RawDir | Out-Null
$Tmp    = Join-Path $env:TEMP ('pcs_' + [guid]::NewGuid().ToString('N').Substring(0,8) + '.png')

function C([int]$r,[int]$g,[int]$b){ [System.Drawing.Color]::FromArgb($r,$g,$b) }
$clBg=C 243 245 249; $clHead=C 31 41 55; $clCard=C 255 255 255; $clText=C 17 24 39
$clSub=C 107 114 128; $clGreen=C 22 163 74; $clGreenH=C 18 140 63
$clBlue=C 37 99 235; $clBlueH=C 29 78 216; $clGray=C 90 98 112; $clGrayH=C 70 78 92
$clOrange=C 217 119 6; $clOrangeH=C 180 98 4; $clRed=C 220 38 38

# ---------- ADB ----------
function Find-Adb {
    $cands = @(
        (Join-Path $Root 'adb\adb.exe'),
        "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
        'C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe',
        'D:\LDPlayer\LDPlayer9\adb.exe'
    )
    foreach ($c in $cands) { if (Test-Path $c) { return $c } }
    $cmd = Get-Command adb.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}
$Adb = Find-Adb
$script:Phone = $null
$script:PhoneState = $null       # 'device' / 'unauthorized' / 'offline' / $null
function Get-Phone {
    $script:PhoneState = $null
    if (-not $Adb) { return $null }
    foreach ($l in (& $Adb devices 2>$null)) {
        if ($l -match '^(\S+)\s+(device|unauthorized|offline)$') {
            $s=$Matches[1]; $st=$Matches[2]
            if ($s -match '^emulator-' -or $s -match '^127\.0\.0\.1') { continue }
            $script:PhoneState = $st
            if ($st -eq 'device') { return $s }
        }
    }
    return $null
}
function Adbs { param([string[]]$a) if ($Phone) { & $Adb -s $Phone @a 2>$null } }

# Info layar HP: ukuran & density fisik (asli) dan override (yang sedang aktif).
function Get-DisplayInfo {
    if (-not $Phone) { return $null }
    $s = (& $Adb -s $Phone shell wm size 2>$null) -join "`n"
    $d = (& $Adb -s $Phone shell wm density 2>$null) -join "`n"
    $i = @{ pw=0; ph=0; pd=0; w=0; h=0; d=0 }
    if ($s -match 'Physical size:\s*(\d+)x(\d+)') { $i.pw=[int]$Matches[1]; $i.ph=[int]$Matches[2] }
    if ($d -match 'Physical density:\s*(\d+)')    { $i.pd=[int]$Matches[1] }
    $i.w=$i.pw; $i.h=$i.ph; $i.d=$i.pd
    if ($s -match 'Override size:\s*(\d+)x(\d+)') { $i.w=[int]$Matches[1]; $i.h=[int]$Matches[2] }
    if ($d -match 'Override density:\s*(\d+)')    { $i.d=[int]$Matches[1] }
    if ($i.pw -le 0 -or $i.pd -le 0) { return $null }
    return $i
}
function Get-Size {
    $i = Get-DisplayInfo
    if (-not $i) { return '-' }
    $zoom = [Math]::Round(100.0 * ($i.d / $i.pd) / ($i.w / $i.pw))
    return ('{0}x{1}  |  {2} dpi  |  tampilan {3}%' -f $i.w,$i.h,$i.d,$zoom)
}

# Resolusi dinaikkan 2x dari layar fisik (rasio layar tetap sama, jadi tidak gepeng),
# sisi panjang dibatasi 4096 px (batas tekstur GPU kebanyakan HP).
# Density ikut dikali faktor yang sama x zoom:
#   zoom 100% = isi layar sama seperti biasa, hanya piksel lebih rapat (lebih tajam)
#   zoom >100% = isi layar (foto) tampil lebih besar, resolusi TETAP tinggi
function Set-HiRes([double]$zoom) {
    $i = Get-DisplayInfo
    if (-not $i) { return $null }
    $long = [Math]::Max($i.pw, $i.ph)
    $k = [Math]::Min(2.0, 4096.0 / $long); if ($k -lt 1) { $k = 1.0 }
    $nw = [int]([Math]::Round($i.pw * $k / 2) * 2)          # dibulatkan ke angka genap
    $nh = [int]([Math]::Round($i.ph * $k / 2) * 2)
    $nd = [int][Math]::Round($i.pd * $k * $zoom)
    Adbs @('shell','wm','size',"${nw}x${nh}") | Out-Null
    Adbs @('shell','wm','density',"$nd") | Out-Null
    return @{ w=$nw; h=$nh; d=$nd }
}

# ---------- gambar ----------
function Load-BitmapNoLock([string]$path) {
    $bytes = [System.IO.File]::ReadAllBytes($path)
    $ms = New-Object System.IO.MemoryStream (,$bytes)
    $img = [System.Drawing.Image]::FromStream($ms)
    $bmp = New-Object System.Drawing.Bitmap $img
    $img.Dispose(); $ms.Dispose(); return $bmp
}
function Grab-Screen {
    if (-not $Phone) { return $null }
    Remove-Item $Tmp -ErrorAction SilentlyContinue   # jangan sampai memuat screenshot lama bila pull gagal
    & $Adb -s $Phone shell input keyevent KEYCODE_WAKEUP 2>$null | Out-Null
    & $Adb -s $Phone shell screencap -p /sdcard/_pcs_tmp.png 2>$null | Out-Null
    & $Adb -s $Phone pull /sdcard/_pcs_tmp.png $Tmp 2>$null | Out-Null
    & $Adb -s $Phone shell rm /sdcard/_pcs_tmp.png 2>$null | Out-Null
    if (-not (Test-Path $Tmp)) { return $null }
    return (Load-BitmapNoLock $Tmp)
}
# auto-crop (cadangan, untuk 1 foto layar penuh)
function Crop-Photo([System.Drawing.Bitmap]$img) {
    $w=$img.Width; $h=$img.Height
    $isPhoto = { param($y) $hits=0; for ($x=0;$x -lt $w;$x+=24){ $c=$img.GetPixel($x,$y); $mx=[Math]::Max($c.R,[Math]::Max($c.G,$c.B)); $mn=[Math]::Min($c.R,[Math]::Min($c.G,$c.B)); if ($mx -gt 40 -and $mn -lt 246){$hits++} }; return ($hits -ge 10) }
    $bS=0;$bE=0;$st=-1
    for ($y=0;$y -lt $h;$y+=2){ if (& $isPhoto $y){ if($st -lt 0){$st=$y} } elseif($st -ge 0){ if(($y-$st) -gt ($bE-$bS)){$bS=$st;$bE=$y}; $st=-1 } }
    if ($st -ge 0 -and (($h-$st) -gt ($bE-$bS))){$bS=$st;$bE=$h}
    if (($bE-$bS) -lt 200){ return $null }
    return $img.Clone((New-Object System.Drawing.Rectangle 0,$bS,$w,($bE-$bS)), $img.PixelFormat)
}

# ================= UI =================
$f = New-Object System.Windows.Forms.Form
$f.Text='Phone Capture Studio'; $f.Size=New-Object System.Drawing.Size(960,790)
$f.MinimumSize=New-Object System.Drawing.Size(880,720); $f.StartPosition='CenterScreen'
$f.BackColor=$clBg; $f.Font=New-Object System.Drawing.Font('Segoe UI',9.75)

$head=New-Object System.Windows.Forms.Panel; $head.Dock='Top'; $head.Height=60; $head.BackColor=$clHead; $f.Controls.Add($head)
$title=New-Object System.Windows.Forms.Label; $title.Text='  Phone Capture Studio'; $title.ForeColor=[System.Drawing.Color]::White
$title.Font=New-Object System.Drawing.Font('Segoe UI',15,[System.Drawing.FontStyle]::Bold); $title.AutoSize=$true; $title.Location=New-Object System.Drawing.Point(16,8); $head.Controls.Add($title)
$subtitle=New-Object System.Windows.Forms.Label; $subtitle.Text='Tarik kotak di pratinjau untuk memilih foto, lalu Simpan'; $subtitle.ForeColor=C 156 163 175; $subtitle.AutoSize=$true; $subtitle.Location=New-Object System.Drawing.Point(19,34); $head.Controls.Add($subtitle)
$pill=New-Object System.Windows.Forms.Label; $pill.AutoSize=$false; $pill.Size=New-Object System.Drawing.Size(250,30); $pill.TextAlign='MiddleCenter'
$pill.Font=New-Object System.Drawing.Font('Segoe UI',9.5,[System.Drawing.FontStyle]::Bold); $pill.ForeColor=[System.Drawing.Color]::White
$pill.Anchor='Top,Right'; $pill.Location=New-Object System.Drawing.Point(($f.ClientSize.Width-266),15); $head.Controls.Add($pill)

# preview
$pvCard=New-Object System.Windows.Forms.Panel; $pvCard.Location=New-Object System.Drawing.Point(16,76); $pvCard.Size=New-Object System.Drawing.Size(560,650)
$pvCard.Anchor='Top,Bottom,Left,Right'; $pvCard.BackColor=$clCard; $pvCard.BorderStyle='FixedSingle'; $f.Controls.Add($pvCard)
$pvBar=New-Object System.Windows.Forms.Panel; $pvBar.Dock='Top'; $pvBar.Height=34; $pvBar.Width=$pvCard.ClientSize.Width; $pvBar.BackColor=C 249 250 251; $pvCard.Controls.Add($pvBar)
$pvHead=New-Object System.Windows.Forms.Label; $pvHead.Text='  Pratinjau Layar HP    Ctrl+roda = zoom  |  klik kanan = geser'; $pvHead.Dock='Fill'; $pvHead.TextAlign='MiddleLeft'
$pvHead.Font=New-Object System.Drawing.Font('Segoe UI',9,[System.Drawing.FontStyle]::Bold); $pvHead.ForeColor=$clText; $pvBar.Controls.Add($pvHead)
$cmbPv=New-Object System.Windows.Forms.ComboBox; $cmbPv.DropDownStyle='DropDownList'; $cmbPv.Size=New-Object System.Drawing.Size(104,24); $cmbPv.Anchor='Top,Right'
$cmbPv.Location=New-Object System.Drawing.Point(($pvBar.Width-110),5)
[void]$cmbPv.Items.AddRange(@('Pas layar','50%','75%','100% (1:1)','150%','200%','300%')); $cmbPv.SelectedIndex=0; $pvBar.Controls.Add($cmbPv); $cmbPv.BringToFront()
$PvLevels=[double[]]@(0,0.5,0.75,1,1.5,2,3)     # 0 = pas layar
# gambar di dalam panel yang bisa digulir; saat zoom, PictureBox dibesarkan sesuai skala
$pvScroll=New-Object System.Windows.Forms.Panel; $pvScroll.Dock='Fill'; $pvScroll.AutoScroll=$true; $pvScroll.BackColor=C 17 24 39; $pvCard.Controls.Add($pvScroll); $pvScroll.BringToFront()
$pic=New-Object System.Windows.Forms.PictureBox; $pic.Dock='Fill'; $pic.SizeMode='Zoom'; $pic.BackColor=C 17 24 39; $pic.Cursor='Cross'; $pvScroll.Controls.Add($pic)

# panel kanan
$side=New-Object System.Windows.Forms.Panel; $side.Location=New-Object System.Drawing.Point(592,76); $side.Size=New-Object System.Drawing.Size(336,650); $side.Anchor='Top,Bottom,Right'; $side.BackColor=$clBg; $f.Controls.Add($side)
function New-Card($y,$h,$t){ $c=New-Object System.Windows.Forms.Panel; $c.Location=New-Object System.Drawing.Point(0,$y); $c.Size=New-Object System.Drawing.Size(336,$h); $c.BackColor=$clCard; $c.BorderStyle='FixedSingle'; $side.Controls.Add($c)
    if($t){ $l=New-Object System.Windows.Forms.Label; $l.UseMnemonic=$false; $l.Text=$t; $l.AutoSize=$true; $l.Location=New-Object System.Drawing.Point(12,8); $l.ForeColor=$clSub; $l.Font=New-Object System.Drawing.Font('Segoe UI',8.5,[System.Drawing.FontStyle]::Bold); $c.Controls.Add($l) }; return $c }
function Style-Btn($b,$bg,$bgH){ $b.FlatStyle='Flat'; $b.FlatAppearance.BorderSize=0; $b.BackColor=$bg; $b.ForeColor=[System.Drawing.Color]::White; $b.Font=New-Object System.Drawing.Font('Segoe UI',10,[System.Drawing.FontStyle]::Bold); $b.Cursor='Hand'; $b.Tag=@{base=$bg;hover=$bgH}; $b.Add_MouseEnter([System.EventHandler]{param($s,$e)$s.BackColor=$s.Tag.hover}); $b.Add_MouseLeave([System.EventHandler]{param($s,$e)$s.BackColor=$s.Tag.base}) }

$cardConn=New-Card 0 64 'STATUS'
$lblConn=New-Object System.Windows.Forms.Label; $lblConn.Location=New-Object System.Drawing.Point(12,28); $lblConn.Size=New-Object System.Drawing.Size(312,28); $lblConn.Font=New-Object System.Drawing.Font('Segoe UI',10,[System.Drawing.FontStyle]::Bold); $cardConn.Controls.Add($lblConn)

$cardRes=New-Card 76 150 'RESOLUSI & UKURAN TAMPILAN HP'
$lblRes=New-Object System.Windows.Forms.Label; $lblRes.Location=New-Object System.Drawing.Point(12,26); $lblRes.AutoSize=$true; $lblRes.Font=New-Object System.Drawing.Font('Segoe UI',10,[System.Drawing.FontStyle]::Bold); $lblRes.ForeColor=$clText; $cardRes.Controls.Add($lblRes)
$lblZoom=New-Object System.Windows.Forms.Label; $lblZoom.Text='Perbesar tampilan:'; $lblZoom.Location=New-Object System.Drawing.Point(12,58); $lblZoom.AutoSize=$true; $lblZoom.ForeColor=$clText; $cardRes.Controls.Add($lblZoom)
$cmbZoom=New-Object System.Windows.Forms.ComboBox; $cmbZoom.DropDownStyle='DropDownList'; $cmbZoom.Location=New-Object System.Drawing.Point(140,54); $cmbZoom.Size=New-Object System.Drawing.Size(184,28)
[void]$cmbZoom.Items.AddRange(@('100% (normal, tajam)','125%','150%','175%','200%')); $cmbZoom.SelectedIndex=0; $cardRes.Controls.Add($cmbZoom)
$btnHi=New-Object System.Windows.Forms.Button; $btnHi.Text='Terapkan (HD x2)'; $btnHi.Location=New-Object System.Drawing.Point(12,90); $btnHi.Size=New-Object System.Drawing.Size(152,46); Style-Btn $btnHi $clBlue $clBlueH; $cardRes.Controls.Add($btnHi)
$btnNorm=New-Object System.Windows.Forms.Button; $btnNorm.Text='Normal (reset)'; $btnNorm.Location=New-Object System.Drawing.Point(172,90); $btnNorm.Size=New-Object System.Drawing.Size(152,46); Style-Btn $btnNorm $clOrange $clOrangeH; $cardRes.Controls.Add($btnNorm)

$btnPrev=New-Object System.Windows.Forms.Button; $btnPrev.Text='1. AMBIL LAYAR'; $btnPrev.Location=New-Object System.Drawing.Point(0,238); $btnPrev.Size=New-Object System.Drawing.Size(336,52); Style-Btn $btnPrev $clGray $clGrayH; $side.Controls.Add($btnPrev)
$btnSave=New-Object System.Windows.Forms.Button; $btnSave.Text='2. SIMPAN AREA TERPILIH'; $btnSave.Location=New-Object System.Drawing.Point(0,298); $btnSave.Size=New-Object System.Drawing.Size(336,60); Style-Btn $btnSave $clGreen $clGreenH; $btnSave.Font=New-Object System.Drawing.Font('Segoe UI',11,[System.Drawing.FontStyle]::Bold); $side.Controls.Add($btnSave)
$btnRaw=New-Object System.Windows.Forms.Button; $btnRaw.Text='Simpan Layar Penuh (asli, tanpa potong)'; $btnRaw.Location=New-Object System.Drawing.Point(0,366); $btnRaw.Size=New-Object System.Drawing.Size(336,46); Style-Btn $btnRaw (C 124 58 237) (C 109 40 217); $btnRaw.Font=New-Object System.Drawing.Font('Segoe UI',9.5,[System.Drawing.FontStyle]::Bold); $side.Controls.Add($btnRaw)
$btnAuto=New-Object System.Windows.Forms.Button; $btnAuto.Text='Potong Otomatis (1 foto penuh)'; $btnAuto.Location=New-Object System.Drawing.Point(0,420); $btnAuto.Size=New-Object System.Drawing.Size(336,34); Style-Btn $btnAuto $clBlue $clBlueH; $btnAuto.Font=New-Object System.Drawing.Font('Segoe UI',9,[System.Drawing.FontStyle]::Bold); $side.Controls.Add($btnAuto)

$cardOut=New-Card 464 64 'HASIL TERSIMPAN'
$lblCount=New-Object System.Windows.Forms.Label; $lblCount.Location=New-Object System.Drawing.Point(12,26); $lblCount.AutoSize=$true; $lblCount.Font=New-Object System.Drawing.Font('Segoe UI',11,[System.Drawing.FontStyle]::Bold); $lblCount.ForeColor=$clGreen; $cardOut.Controls.Add($lblCount)
$btnOpen=New-Object System.Windows.Forms.Button; $btnOpen.Text='Buka Folder'; $btnOpen.Location=New-Object System.Drawing.Point(204,22); $btnOpen.Size=New-Object System.Drawing.Size(120,34); Style-Btn $btnOpen $clBlue $clBlueH; $cardOut.Controls.Add($btnOpen)
$gal=New-Object System.Windows.Forms.FlowLayoutPanel; $gal.Location=New-Object System.Drawing.Point(0,540); $gal.Size=New-Object System.Drawing.Size(336,110); $gal.Anchor='Top,Bottom,Right'; $gal.BackColor=$clCard; $gal.BorderStyle='FixedSingle'; $gal.AutoScroll=$true; $side.Controls.Add($gal)

$toast=New-Object System.Windows.Forms.Label; $toast.Dock='Bottom'; $toast.Height=30; $toast.TextAlign='MiddleLeft'; $toast.Font=New-Object System.Drawing.Font('Segoe UI',9.5); $toast.ForeColor=$clText; $toast.BackColor=C 236 253 245; $toast.Padding=New-Object System.Windows.Forms.Padding(12,0,0,0); $f.Controls.Add($toast)

# ---------- state & logika ----------
$script:count=(Get-ChildItem $OutDir -Filter 'foto_*.png' -ErrorAction SilentlyContinue).Count
$script:rawCount=(Get-ChildItem $RawDir -Filter '*.png' -ErrorAction SilentlyContinue).Count
$script:curFull=$null          # Bitmap layar penuh saat ini
$script:dragging=$false
$script:selA=New-Object System.Drawing.Point 0,0     # titik seleksi, dalam koordinat PIKSEL GAMBAR asli
$script:selB=New-Object System.Drawing.Point 0,0
$script:hasSel=$false
$script:pvZoom=0.0             # 0 = pas layar, selain itu skala tampilan (1 = 1 piksel HP : 1 piksel PC)
$script:pvBusy=$false
$script:pvApplying=$false
$script:panning=$false

function Say($m,$ok){ $toast.Text=$m; if($ok){$toast.BackColor=C 236 253 245;$toast.ForeColor=C 6 95 70}else{$toast.BackColor=C 254 242 242;$toast.ForeColor=C 153 27 27} }
function Update-Count{ $lblCount.Text="$($script:count) foto" }
function Add-Thumb($path){ try{ $tb=New-Object System.Windows.Forms.PictureBox; $tb.Size=New-Object System.Drawing.Size(64,96); $tb.SizeMode='Zoom'; $tb.Cursor='Hand'; $tb.Margin=New-Object System.Windows.Forms.Padding(6); $full=Load-BitmapNoLock $path; $k=[Math]::Min(128/$full.Width,192/$full.Height); $tb.Image=New-Object System.Drawing.Bitmap $full,([Math]::Max(1,[int]($full.Width*$k))),([Math]::Max(1,[int]($full.Height*$k))); $full.Dispose();   # simpan thumbnail kecil saja, bukan gambar penuh (hemat memori)
 $tb.Tag=$path; $tb.Add_Click([System.EventHandler]{param($s,$e) Start-Process $s.Tag}); $gal.Controls.Add($tb); $gal.Controls.SetChildIndex($tb,0) }catch{} }
function Set-Preview([System.Drawing.Bitmap]$bmp){ if($pic.Image){$pic.Image.Dispose()}; $pic.Image=$bmp; Apply-PvZoom $null }
function Refresh-Status{
    $script:Phone=Get-Phone
    if(-not $Adb){ $pill.Text='ADB tidak ada'; $pill.BackColor=$clRed; $lblConn.Text='ADB tidak ditemukan'; $lblConn.ForeColor=$clRed; $lblRes.Text='-'; return }
    if(-not $Phone -and $script:PhoneState -eq 'unauthorized'){ $pill.Text='Izinkan debugging di HP'; $pill.BackColor=$clOrange; $lblConn.Text='Ketuk "Izinkan" di layar HP'; $lblConn.ForeColor=$clOrange; $lblRes.Text='-'; return }
    if(-not $Phone){ $pill.Text='HP tidak terhubung'; $pill.BackColor=$clRed; $lblConn.Text='Sambungkan USB + izinkan debug'; $lblConn.ForeColor=$clRed; $lblRes.Text='-'; return }
    $pill.Text="Terhubung: $Phone"; $pill.BackColor=$clGreen; $lblConn.Text='HP siap'; $lblConn.ForeColor=$clGreen; $lblRes.Text=Get-Size
}
# pemetaan koordinat PictureBox(Zoom) -> piksel gambar
function Img-Geom{
    if(-not $pic.Image){ return $null }
    $cw=$pic.ClientSize.Width; $ch=$pic.ClientSize.Height; $iw=$pic.Image.Width; $ih=$pic.Image.Height
    $scale=[Math]::Min($cw/$iw,$ch/$ih); $dw=$iw*$scale; $dh=$ih*$scale
    return @{ scale=$scale; offX=($cw-$dw)/2; offY=($ch-$dh)/2; iw=$iw; ih=$ih }
}
function Client-To-Img($p){ $g=Img-Geom; if(-not $g){return $null}; $ix=[int][Math]::Round(($p.X-$g.offX)/$g.scale); $iy=[int][Math]::Round(($p.Y-$g.offY)/$g.scale); $ix=[Math]::Max(0,[Math]::Min($g.iw,$ix)); $iy=[Math]::Max(0,[Math]::Min($g.ih,$iy)); return New-Object System.Drawing.Point $ix,$iy }

# ---------- zoom pratinjau (hanya tampilan di PC; file yang disimpan selalu dari resolusi asli) ----------
function Fit-Scale{ if(-not $pic.Image){return 1}; return [Math]::Min($pvScroll.ClientSize.Width/$pic.Image.Width, $pvScroll.ClientSize.Height/$pic.Image.Height) }
# $anchor = titik (koordinat pvScroll) yang posisinya di gambar dipertahankan saat zoom; $null = tengah
function Apply-PvZoom($anchor){
    if($script:pvApplying){ return }
    if(-not $pic.Image -or $script:pvZoom -le 0){ $pic.Dock='Fill'; $pic.Invalidate(); return }
    $script:pvApplying=$true
    try{
        $vw=$pvScroll.ClientSize.Width; $vh=$pvScroll.ClientSize.Height
        if(-not $anchor){ $anchor=New-Object System.Drawing.Point ([int]($vw/2)),([int]($vh/2)) }
        $g=Img-Geom
        $pp=$pic.PointToClient($pvScroll.PointToScreen($anchor))
        $fx=($pp.X-$g.offX)/$g.scale; $fy=($pp.Y-$g.offY)/$g.scale          # titik gambar di bawah anchor
        $z=$script:pvZoom; $nw=[int][Math]::Round($g.iw*$z); $nh=[int][Math]::Round($g.ih*$z)
        $ox=[Math]::Max(0,[int](($vw-$nw)/2)); $oy=[Math]::Max(0,[int](($vh-$nh)/2))   # tengahkan bila lebih kecil
        $pvScroll.SuspendLayout()
        $pvScroll.AutoScrollPosition=New-Object System.Drawing.Point 0,0
        $pic.Dock='None'; $pic.Location=New-Object System.Drawing.Point $ox,$oy; $pic.Size=New-Object System.Drawing.Size $nw,$nh
        $pvScroll.ResumeLayout()
        $sx=[int]($ox+$fx*$z-$anchor.X); $sy=[int]($oy+$fy*$z-$anchor.Y)
        $pvScroll.AutoScrollPosition=New-Object System.Drawing.Point ([Math]::Max(0,$sx)),([Math]::Max(0,$sy))
        $pic.Invalidate()
    } finally { $script:pvApplying=$false }
}
function Sync-PvCombo{ $script:pvBusy=$true; $cmbPv.SelectedIndex=[Array]::IndexOf($PvLevels,$script:pvZoom); $script:pvBusy=$false }
function Step-PvZoom([int]$dir,$anchor){
    if(-not $pic.Image -or $dir -eq 0){ return }
    $cur=$script:pvZoom; if($cur -le 0){ $cur=Fit-Scale }
    $lv=[double[]]@(0.5,0.75,1,1.5,2,3)
    if($dir -gt 0){ $n=$lv | Where-Object { $_ -gt $cur*1.01 } | Select-Object -First 1; if(-not $n){ return } }
    else { $n=$lv | Where-Object { $_ -lt $cur*0.99 } | Select-Object -Last 1; if(-not $n -or $n -le (Fit-Scale)){ $n=0 } }
    $script:pvZoom=[double]$n; Sync-PvCombo; Apply-PvZoom $anchor
}
$cmbPv.Add_SelectedIndexChanged({
    if($script:pvBusy){ return }
    $script:pvZoom=[double]$PvLevels[$cmbPv.SelectedIndex]; Apply-PvZoom $null
    if($script:hasSel -and $script:pvZoom -gt 0){      # pusatkan tampilan ke kotak yang sudah dipilih
        $cx=($script:selA.X+$script:selB.X)/2; $cy=($script:selA.Y+$script:selB.Y)/2
        $sx=$pic.Left-$pvScroll.AutoScrollPosition.X+$cx*$script:pvZoom-$pvScroll.ClientSize.Width/2
        $sy=$pic.Top-$pvScroll.AutoScrollPosition.Y+$cy*$script:pvZoom-$pvScroll.ClientSize.Height/2
        $pvScroll.AutoScrollPosition=New-Object System.Drawing.Point ([int][Math]::Max(0,$sx)),([int][Math]::Max(0,$sy))
    }
})
$pvScroll.Add_Resize({ if($script:pvZoom -gt 0){ Apply-PvZoom $null } })

$pic.Add_MouseDown({ param($s,$e)
    if(-not $pic.Image){ return }
    if($e.Button -eq 'Left'){ $script:dragging=$true; $p=Client-To-Img $e.Location; $script:selA=$p; $script:selB=$p; $script:hasSel=$true; $pic.Invalidate() }
    elseif($e.Button -eq 'Right' -and $script:pvZoom -gt 0){
        $script:panning=$true; $script:panFrom=[System.Windows.Forms.Cursor]::Position
        $script:panScroll=New-Object System.Drawing.Point (-$pvScroll.AutoScrollPosition.X),(-$pvScroll.AutoScrollPosition.Y); $pic.Cursor='SizeAll'
    }
})
$pic.Add_MouseMove({ param($s,$e)
    $cur=[System.Windows.Forms.Cursor]::Position
    if($script:panning){
        $pvScroll.AutoScrollPosition=New-Object System.Drawing.Point ($script:panScroll.X-($cur.X-$script:panFrom.X)),($script:panScroll.Y-($cur.Y-$script:panFrom.Y)); return
    }
    if($script:dragging){
        # gulir otomatis bila kotak ditarik melewati tepi pratinjau
        $v=$pvScroll.PointToClient($cur); $dx=0; $dy=0
        if($v.X -lt 0){$dx=$v.X} elseif($v.X -gt $pvScroll.ClientSize.Width){$dx=$v.X-$pvScroll.ClientSize.Width}
        if($v.Y -lt 0){$dy=$v.Y} elseif($v.Y -gt $pvScroll.ClientSize.Height){$dy=$v.Y-$pvScroll.ClientSize.Height}
        if($dx -ne 0 -or $dy -ne 0){ $pvScroll.AutoScrollPosition=New-Object System.Drawing.Point ((-$pvScroll.AutoScrollPosition.X)+$dx),((-$pvScroll.AutoScrollPosition.Y)+$dy) }
        $script:selB=Client-To-Img ($pic.PointToClient($cur)); $pic.Invalidate()
    }
})
$pic.Add_MouseUp({ param($s,$e)
    if($script:panning -and $e.Button -eq 'Right'){ $script:panning=$false; $pic.Cursor='Cross'; return }
    if($script:dragging -and $e.Button -eq 'Left'){ $script:dragging=$false; $pic.Invalidate(); Say 'Area dipilih. Klik "2. SIMPAN AREA TERPILIH".' $true }
})
$pic.Add_MouseWheel({ param($s,$e)
    $ctrl=[System.Windows.Forms.Keys]::Control
    if(([System.Windows.Forms.Control]::ModifierKeys -band $ctrl) -eq $ctrl){
        $e.Handled=$true      # jangan ikut menggulir panel
        Step-PvZoom ([Math]::Sign($e.Delta)) ($pvScroll.PointToClient([System.Windows.Forms.Cursor]::Position))
    }
})
$pic.Add_Paint({ param($s,$e)
    if(-not $script:hasSel){ return }; $g=Img-Geom; if(-not $g){ return }
    $iw=[Math]::Abs($script:selA.X-$script:selB.X); $ih=[Math]::Abs($script:selA.Y-$script:selB.Y)
    $x=[single]($g.offX+[Math]::Min($script:selA.X,$script:selB.X)*$g.scale); $y=[single]($g.offY+[Math]::Min($script:selA.Y,$script:selB.Y)*$g.scale)
    $w=[single]($iw*$g.scale); $h=[single]($ih*$g.scale)
    if($w -gt 2 -and $h -gt 2){
        $br=New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(40,22,163,74)); $e.Graphics.FillRectangle($br,$x,$y,$w,$h); $br.Dispose()
        $pen=New-Object System.Drawing.Pen ((C 22 163 74),2); $e.Graphics.DrawRectangle($pen,$x,$y,$w,$h); $pen.Dispose()
        # ukuran hasil (piksel asli) di pojok kotak
        $txt="{0} x {1} px" -f $iw,$ih; $fnt=New-Object System.Drawing.Font('Segoe UI',9,[System.Drawing.FontStyle]::Bold)
        $sz=$e.Graphics.MeasureString($txt,$fnt); $ty=[single][Math]::Max(0,$y-$sz.Height-2)
        $bg=New-Object System.Drawing.SolidBrush (C 22 163 74); $e.Graphics.FillRectangle($bg,$x,$ty,$sz.Width,$sz.Height); $bg.Dispose()
        $e.Graphics.DrawString($txt,$fnt,[System.Drawing.Brushes]::White,$x,$ty); $fnt.Dispose()
    }
})

$btnPrev.Add_Click({ Refresh-Status; if(-not $Phone){Say 'HP tidak terhubung.' $false;return}; Say 'Mengambil layar...' $true; $f.Refresh(); $b=Grab-Screen; if($b){ if($script:curFull){$script:curFull.Dispose()}; $script:curFull=$b; $script:hasSel=$false; Set-Preview (New-Object System.Drawing.Bitmap $b); Say ("Layar {0}x{1} siap. Tarik kotak di foto yang mau disimpan." -f $b.Width,$b.Height) $true }else{Say 'Gagal mengambil layar.' $false} })

$btnSave.Add_Click({
    if(-not $script:curFull){ Say 'Klik "1. AMBIL LAYAR" dulu.' $false; return }
    if(-not $script:hasSel){ Say 'Tarik kotak dulu di pratinjau untuk memilih area.' $false; return }
    $a=$script:selA; $b=$script:selB      # sudah dalam piksel gambar asli
    $x=[Math]::Min($a.X,$b.X); $y=[Math]::Min($a.Y,$b.Y); $w=[Math]::Abs($a.X-$b.X); $h=[Math]::Abs($a.Y-$b.Y)
    if($w -lt 20 -or $h -lt 20){ Say 'Kotak terlalu kecil. Tarik lebih lebar.' $false; return }
    $crop=$script:curFull.Clone((New-Object System.Drawing.Rectangle $x,$y,$w,$h), $script:curFull.PixelFormat)
    $stamp=Get-Date -Format 'yyyyMMdd_HHmmss_fff'; $dest=Join-Path $OutDir "foto_$stamp.png"; $crop.Save($dest,[System.Drawing.Imaging.ImageFormat]::Png)
    $script:count++; Update-Count; Add-Thumb $dest; Say ("Tersimpan #{0}: foto_{1}.png ({2}x{3})" -f $script:count,$stamp,$w,$h) $true; $crop.Dispose()
})

$btnAuto.Add_Click({
    Refresh-Status; if(-not $Phone){Say 'HP tidak terhubung.' $false;return}
    Say 'Mengambil & memotong otomatis...' $true; $f.Refresh()
    $full=Grab-Screen; if(-not $full){Say 'Gagal mengambil layar.' $false;return}
    if($script:curFull){$script:curFull.Dispose()}; $script:curFull=$full; $script:hasSel=$false; Set-Preview (New-Object System.Drawing.Bitmap $full)
    $crop=Crop-Photo $full
    if(-not $crop){ Say 'Auto gagal. Pakai cara pilih kotak manual.' $false; return }
    $stamp=Get-Date -Format 'yyyyMMdd_HHmmss_fff'; $dest=Join-Path $OutDir "foto_$stamp.png"; $crop.Save($dest,[System.Drawing.Imaging.ImageFormat]::Png)
    $script:count++; Update-Count; Add-Thumb $dest; Say ("Tersimpan #{0} (auto): foto_{1}.png ({2}x{3})" -f $script:count,$stamp,$crop.Width,$crop.Height) $true; $crop.Dispose()
})

$btnRaw.Add_Click({ Refresh-Status; if(-not $Phone){Say 'HP tidak terhubung.' $false;return}; Say 'Menyimpan layar penuh asli...' $true; $f.Refresh(); $b=Grab-Screen; if(-not $b){Say 'Gagal mengambil layar.' $false;return}; if($script:curFull){$script:curFull.Dispose()}; $script:curFull=$b; $script:hasSel=$false; Set-Preview (New-Object System.Drawing.Bitmap $b); $stamp=Get-Date -Format 'yyyyMMdd_HHmmss_fff'; $dest=Join-Path $RawDir "layar_$stamp.png"; $b.Save($dest,[System.Drawing.Imaging.ImageFormat]::Png); $script:rawCount++; Say ("Layar asli #{0} disimpan: layar_{1}.png ({2}x{3}). Buka foto berikutnya lalu klik lagi." -f $script:rawCount,$stamp,$b.Width,$b.Height) $true })

$btnHi.Add_Click({
    Refresh-Status; if(-not $Phone){Say 'HP tidak terhubung.' $false;return}
    $zoom=@(1.0,1.25,1.5,1.75,2.0)[$cmbZoom.SelectedIndex]
    $r=Set-HiRes $zoom
    if(-not $r){ Say 'Gagal membaca ukuran layar HP.' $false; return }
    $lblRes.Text=Get-Size
    Say ("Layar HP: {0}x{1}, {2} dpi, tampilan {3}%. Buka lagi fotonya di HP lalu AMBIL LAYAR." -f $r.w,$r.h,$r.d,[int]($zoom*100)) $true
})
$btnNorm.Add_Click({ Refresh-Status; if(-not $Phone){Say 'HP tidak terhubung.' $false;return}; Adbs @('shell','wm','size','reset')|Out-Null; Adbs @('shell','wm','density','reset')|Out-Null; $lblRes.Text=Get-Size; Say 'Resolusi dikembalikan ke normal.' $true })
$btnOpen.Add_Click({ Start-Process explorer.exe $OutDir })

Get-ChildItem $OutDir -Filter 'foto_*.png' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | ForEach-Object { Add-Thumb $_.FullName }
$f.Add_Shown({ Refresh-Status; Update-Count; Say 'Langkah: 1) klik AMBIL LAYAR  2) tarik kotak di foto  3) klik SIMPAN AREA.' $true })
# Ubahan wm size/density tetap aktif di HP walau aplikasi ditutup/kabel dicabut -> tawarkan reset.
$f.Add_FormClosing({ param($s,$e)
    $script:Phone=Get-Phone; $i=Get-DisplayInfo
    if($i -and ($i.w -ne $i.pw -or $i.d -ne $i.pd)){
        $ans=[System.Windows.Forms.MessageBox]::Show("Layar HP masih memakai mode HD ($($i.w)x$($i.h), $($i.d) dpi).`n`nKembalikan layar HP ke normal sekarang?",'Phone Capture Studio','YesNoCancel','Question')
        if($ans -eq 'Cancel'){ $e.Cancel=$true; return }
        if($ans -eq 'Yes'){ Adbs @('shell','wm','size','reset')|Out-Null; Adbs @('shell','wm','density','reset')|Out-Null }
    }
})
$f.Add_FormClosed({ if($pic.Image){$pic.Image.Dispose()}; if($script:curFull){$script:curFull.Dispose()}; Remove-Item $Tmp -ErrorAction SilentlyContinue })
[void]$f.ShowDialog()
