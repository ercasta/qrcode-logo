import os
import sys
try:
    import yaml
except Exception:
    yaml = None

from qrcode_plain import estimate_coverage

cfg_path = 'qr_config.yaml'
cfg = {}
if os.path.exists(cfg_path):
    try:
        if yaml:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f) or {}
        else:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if ':' in line:
                        k, v = line.split(':', 1)
                        cfg[k.strip()] = v.strip().strip('"')
    except Exception as e:
        print('Failed to read config:', e)
        sys.exit(1)
else:
    sample = """# Sample QR config for compute_coverage.py
# Set 'data' to the content or URL encoded in the QR code.
# Set 'logo' to a path to a logo image file, or leave null.
# 'logo_scale' controls logo relative size (0.0-1.0)
data: "https://example.com"
logo: null
logo_scale: 0.312
"""
    try:
        with open(cfg_path, 'w', encoding='utf-8') as f:
            f.write(sample)
        print(f"No config found at {cfg_path}. A sample config has been created.")
        print(f"Please edit {cfg_path} with your values and re-run this script.")
    except Exception as e:
        print('Failed to create sample config:', e)
    sys.exit(1)

data = cfg.get('data', 'https://example.com')
logo = cfg.get('logo')
logo_scale = float(cfg.get('logo_scale', 0.312))
box_size = 10
border = 6

covered, total, coverage_pct = estimate_coverage(data, logo, logo_scale, box_size=box_size, border=border)
# script uses ERROR_CORRECT_H by default
ecc_percent = 30
remaining = ecc_percent - coverage_pct

print(f"data={data}")
print(f"logo={logo}")
print(f"logo_scale={logo_scale}")
print(f"covered={covered}")
print(f"total_modules={total}")
print(f"coverage_pct={coverage_pct:.4f}")
print(f"ecc_capacity={ecc_percent}")
print(f"remaining_ecc_percent={remaining:.4f}")
print(f"remaining_fraction={remaining/100:.4f}")
