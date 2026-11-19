# Membuat PhoneCaptureStudio.exe di akar proyek dari peluncur.cs menggunakan penyusun C# bawaan Windows (csc.exe).
$ErrorActionPreference = "Stop"
$akar = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) { 
    $csc = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe" 
}
if (-not (Test-Path $csc)) { throw "Penyusun C# bawaan Windows tidak ditemukan di $csc" }

$versi = [regex]::Match((Get-Content (Join-Path $akar "app\versi.py") -Raw), 'VERSI = "([\d.]+)"').Groups[1].Value
if (-not $versi) { $versi = "1.0.0" }

$sumber = Join-Path $env:TEMP "pcs_peluncur.cs"
(Get-Content (Join-Path $PSScriptRoot "peluncur.cs") -Raw).Replace("@VERSI@", $versi) | Set-Content $sumber -Encoding UTF8

$targetExe = Join-Path $akar "PhoneCaptureStudio.exe"
$iconPath = Join-Path $akar "app\aset\ikon.ico"

try {
    Write-Host "Menyusun PhoneCaptureStudio.exe..."
    $argList = @("/nologo", "/optimize+", "/target:winexe", "/out:$targetExe", "/reference:System.Windows.Forms.dll")
    if (Test-Path $iconPath) {
        $argList += "/win32icon:$iconPath"
    }
    $argList += $sumber

    & $csc $argList
    if ($LASTEXITCODE -ne 0) { throw "Kompilasi PhoneCaptureStudio.exe gagal dengan kode $LASTEXITCODE" }
    Write-Host "Berhasil membuat $targetExe" -ForegroundColor Green
} finally {
    Remove-Item $sumber -ErrorAction SilentlyContinue
}
