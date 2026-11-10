# VPXmerge for VPX 10.8.1 — Windows x64

The VPX 10.8.1 option exports compatible per-table plugin folders and optional frontend media. It does **not** install VPX, PinMAME, Nixie, or other plugins.

## Download a Windows test build (no local compilation)

1. Open [Actions](https://github.com/buffdriver/VPX-Standalone-Merging-Tool/actions/workflows/windows-x64.yml) on GitHub.
2. Open a successful **Windows x64 Test Build** run for the proposed change.
3. Under **Artifacts**, download `VPXmerge-10.8.1-Windows-x64`.
4. Extract the downloaded ZIP (it contains a second packaged ZIP), then extract `VPXmerge_10_8_1-Windows-x64.zip` to a folder.
5. Run `VPXmerge_10_8_1.exe` from that folder, keeping the `_internal` directory beside it.

The standalone executable doesn't need a Python installation on the target PC.

## Compile it yourself on 64-bit Windows

Install Python 3.11 x64, then from a PowerShell prompt in the cloned repository:

```powershell
py -3.11 -m pip install -r requirements-windows.txt
py -3.11 -m PyInstaller --noconfirm --clean --windowed --onedir --name VPXmerge_10_8_1 --collect-all tkinterdnd2 VPXmerge.py
```

Launch `dist\VPXmerge_10_8_1\VPXmerge_10_8_1.exe`.

## VPX 10.8.1 output changes

- AltSound packs are copied into `altsound/<ROM>/`.
- VNI color packs go into `vni/<ROM>/`, even when a Serum colorization is also found.
- Serum packs are found in legacy VPinMAME `altcolor/<ROM>/` and table-local/new-style `serum/<ROM>/` folders. Both `.cROMc` (preferred) and older `.cRZ` are recognized. The selected file is renamed to `<ROM>.cROMc` or `<ROM>.cRZ` under `serum/<ROM>/`, as VPX's Serum plugin expects.
- Matching source `.vbs` script overrides and `.nix` Nixie layout files are copied next to the table without overwriting existing ones.
- Backglass files named after the containing table folder are detected in addition to those named after the VPX file.
- When **Include Media Files** is enabled, the new **VPX 10.8.1** format writes proposed frontend names such as `medias/(Playfield) Table Name.mp4`. This is optional frontend metadata, not a VPX-player requirement.
- The old **VPinFE** and **PuP Media** choices remain available.

**Test in a new, empty export folder first.** This change was not validated against a full installed pinball cabinet. The GitHub workflow checks Python syntax, Serum path-detection regression tests, and packaging, but not actual table playback. The original release workflow remains unchanged.
