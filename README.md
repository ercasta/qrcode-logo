# QR Code Sheet Generator (Docker helper)

This repository generates A4 SVG/PDF sheets of QR codes and supports embedding a logo.

Quick usage (Windows, PowerShell):

1. Build image (only once):

```powershell
Set-Location 'C:\Users\ercas\creazioni\qrcode-logo'
.\run_in_docker.ps1
```

2. Regenerate outputs after editing `qr_config.yaml` or replacing logo (no rebuild):

```powershell
.\run_no_build.bat --template /app/template_pure.svg --out-svg /output/filled.svg --out-pdf /output/filled.pdf
```

3. Force rebuild and regenerate:

```powershell
.\run_rebuild.bat --template /app/template_pure.svg --out-svg /output/filled.svg --out-pdf /output/filled.pdf
```

Notes:
- The helper script `run_in_docker.ps1` mounts the host repository into the container at `/app` and the host `./output` directory at `/output`, so changes to `qr_config.yaml` or logo files are picked up without rebuilding the image when you use `--no-build`.
- `--no-build` will fail if the `qr-generator` image does not exist; omit it the first time or use `--rebuild` to force a fresh build.
- You can pass any arguments accepted by `generate_qr_sheet.py` (for example `--count`, `--from-file`, or `--template`) after the bat/PS script.

Files of interest:
- `generate_qr_sheet.py` — generator and template filler
- `qrcode_plain.py` — QR + logo generation logic
- `run_in_docker.ps1` — build/run helper (supports `--no-build` and `--rebuild`)
- `run_no_build.bat`, `run_rebuild.bat` — Windows shortcuts
- `Dockerfile` — container image definition

Examples:
- Regenerate using latest host config/logo (no rebuild):

```powershell
.\run_no_build.bat --template /app/template_pure.svg --out-svg /output/updated.svg --out-pdf /output/updated.pdf
```

- Force rebuild (useful after changing `Dockerfile`):

```powershell
.\run_rebuild.bat --template /app/template_pure.svg --out-svg /output/updated.svg --out-pdf /output/updated.pdf
```
