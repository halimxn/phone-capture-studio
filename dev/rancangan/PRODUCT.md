# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Delegated (user allowed leaving PowerShell + WinForms). Chosen: a local web UI — Python
standard-library HTTP server + Pillow, opened as a Microsoft Edge app window
(`msedge --app`) so it looks like a desktop window. Python 3 + Pillow are already installed
on the user's PC. ADB lives in `adb/` (user-supplied, not committed). The PowerShell app `PhoneCaptureStudio.ps1` remains as fallback.

## Users

One person (the owner) using it on their own Windows PC. They plug their Android phone in
over USB, open a photo in an app on the phone that only lets them view it, and save that photo to
the PC — usually many photos in one sitting, one after another.

## Product Purpose

Get photos off the phone screen onto the PC, cropped cleanly and at the highest
resolution the phone can render. Success = each photo saved in a few seconds, correctly
cropped, sharp, with no fiddling.

## Operating Context

- Phone connected via USB debugging (ADB); the app never touches app servers or accounts.
- Workflow per photo: open photo on phone -> capture screen -> select/auto-crop -> save.
- Optional HD mode raises the phone's render resolution 2x (`wm size` / `wm density`) and a
  display zoom (100–200%); must be reset to normal afterwards.
- Output folders: `foto_absensi/` (selected area), `layar_penuh/` (full screen, cropped by
  `proses_layar.py`), `layar_penuh_asli/` (backup), `layar_penuh_hd/` (2x non-AI upscale).

## Capabilities and Constraints

- Capture phone screen, preview it, drag-select an area, save at original pixels.
- Preview zoom (fit, 50–300%), pan, auto-crop of a full-screen photo, save raw screen.
- Phone status (not connected / unauthorized / ready), current resolution/density.
- HD upscale must never alter faces (no AI / generative enhancement).
- UI language: Indonesian.

## Brand Commitments

- Light and clean look (user's explicit preference).
- Name: "Phone Capture Studio" (repo: phone-capture-studio).

## Evidence on Hand

Real captures exist only locally (not committed: they contain faces). No logo or brand assets.

## Product Principles

1. The photo is the content; chrome stays out of its way.
2. One obvious next step at every moment (connect -> capture -> select -> save).
3. Never lose or degrade a photo: originals at full resolution, no face alteration.
4. Leave the phone as it was found (remind to reset HD mode).
