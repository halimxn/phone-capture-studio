@echo off
rem Menyusun PhoneCaptureStudio.exe dari peluncur.cs
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "dev\kemas\buat_peluncur.ps1"
echo.
pause
