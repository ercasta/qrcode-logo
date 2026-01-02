import argparse
import os
import qrcode
from PIL import Image
import cv2
import tempfile
import shutil
try:
    import yaml
except Exception:
    yaml = None


def make_qr(data, out_path, logo_path=None, logo_scale=0.312, box_size=10, border=6):
    img = make_qr_image(data, logo_path=logo_path, logo_scale=logo_scale, box_size=box_size, border=border)
    img.save(out_path)


def make_qr_image(data, logo_path=None, logo_scale=0.312, box_size=10, border=6):
    """Create a QR code PIL Image (RGBA). Returns the Image object.

    This encapsulates the generation and optional logo overlay logic so other
    scripts (like generate_qr_sheet.py) can import and reuse it.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    module_count = len(matrix)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    if logo_path and os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        img_w, img_h = img.size

        max_logo_w = int(img_w * float(logo_scale))
        max_logo_h = int(img_h * float(logo_scale))
        logo.thumbnail((max_logo_w, max_logo_h), Image.LANCZOS)

        lx, ly = logo.size
        pos = ((img_w - lx) // 2, (img_h - ly) // 2)

        # estimate how many QR modules the logo will cover
        border_pixels = border * box_size
        covered = 0
        for r in range(module_count):
            for c in range(module_count):
                cx = border_pixels + c * box_size + box_size / 2
                cy = border_pixels + r * box_size + box_size / 2
                if pos[0] <= cx <= pos[0] + lx and pos[1] <= cy <= pos[1] + ly:
                    covered += 1

        total_modules = module_count * module_count
        coverage_pct = covered / total_modules * 100

        ecc_capacity = {
            qrcode.constants.ERROR_CORRECT_L: 7,
            qrcode.constants.ERROR_CORRECT_M: 15,
            qrcode.constants.ERROR_CORRECT_Q: 25,
            qrcode.constants.ERROR_CORRECT_H: 30,
        }
        ecc_percent = ecc_capacity.get(qrcode.constants.ERROR_CORRECT_H, 30)

        print(f"Logo covers {covered}/{total_modules} modules ({coverage_pct:.2f}%).")
        print(f"Approx. ECC recoverable: {ecc_percent}% (level H).")

        img.paste(logo, pos, logo)

    return img


def decode_image(path):
    img = cv2.imread(path)
    if img is None:
        return ""
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(img)
    return data or ""


def estimate_coverage(data, logo_path, logo_scale, box_size=10, border=6):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    module_count = len(matrix)

    img_w = module_count * box_size + 2 * border * box_size
    img_h = img_w

    if not (logo_path and os.path.exists(logo_path)):
        return 0, module_count * module_count, 0.0

    logo = Image.open(logo_path).convert("RGBA")
    max_logo_w = int(img_w * float(logo_scale))
    max_logo_h = int(img_h * float(logo_scale))
    logo.thumbnail((max_logo_w, max_logo_h), Image.LANCZOS)
    lx, ly = logo.size
    posx = (img_w - lx) // 2
    posy = (img_h - ly) // 2

    border_pixels = border * box_size
    covered = 0
    for r in range(module_count):
        for c in range(module_count):
            cx = border_pixels + c * box_size + box_size / 2
            cy = border_pixels + r * box_size + box_size / 2
            if posx <= cx <= posx + lx and posy <= cy <= posy + ly:
                covered += 1

    total_modules = module_count * module_count
    coverage_pct = covered / total_modules * 100
    return covered, total_modules, coverage_pct


def find_max_logo_scale(data, logo_path, out_path, start=0.05, tol=0.01, max_scale=0.6, box_size=10, border=6, min_ecc_left=None):
    """
    Find maximum logo scale using binary search. `tol` is used as stopping tolerance.
    If `min_ecc_left` is provided, ensure coverage does not exceed ECC_capacity - min_ecc_left.
    """
    ecc_capacity = {
        qrcode.constants.ERROR_CORRECT_L: 7,
        qrcode.constants.ERROR_CORRECT_M: 15,
        qrcode.constants.ERROR_CORRECT_Q: 25,
        qrcode.constants.ERROR_CORRECT_H: 30,
    }
    ecc_percent = ecc_capacity.get(qrcode.constants.ERROR_CORRECT_H, 30)

    allowed_coverage_pct = None
    if min_ecc_left is not None:
        if min_ecc_left < 15:
            print("Warning: requested minimum ECC left is below 15% — decoding may be unreliable.")
        if min_ecc_left >= ecc_percent:
            print(f"Requested minimum ECC left ({min_ecc_left}%) >= ECC capacity ({ecc_percent}%). No feasible logo size.")
            return None
        allowed_coverage_pct = ecc_percent - min_ecc_left

    low = start
    high = max_scale
    best_scale = None
    tmpdir = tempfile.mkdtemp(prefix="qr_test_")
    try:
        tol = max(tol, 0.001)
        iterations = 0
        while (high - low) > tol and iterations < 50:
            mid = (low + high) / 2.0
            covered, total, coverage_pct = estimate_coverage(data, logo_path, mid, box_size=box_size, border=border)
            print(f"Testing scale {mid:.4f}: covers {covered}/{total} modules ({coverage_pct:.2f}%)")

            if allowed_coverage_pct is not None and coverage_pct > allowed_coverage_pct:
                # mid covers too much; shrink
                high = mid
                iterations += 1
                continue

            tmpfile = os.path.join(tmpdir, f"qr_{int(mid*100000)}.png")
            make_qr(data, tmpfile, logo_path=logo_path, logo_scale=mid, box_size=box_size, border=border)
            decoded = decode_image(tmpfile)
            if decoded:
                best_scale = mid
                # try larger
                low = mid
            else:
                # too large to decode, reduce
                high = mid

            iterations += 1

        if best_scale:
            # generate final image at best_scale
            make_qr(data, out_path, logo_path=logo_path, logo_scale=best_scale, box_size=box_size, border=border)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return best_scale


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate QR code with optional center logo.")
    parser.add_argument("data", nargs="?", default="https://example.com", help="Data/URL for QR code")
    parser.add_argument("--config", default="qr_config.yaml", help="Path to YAML config file with defaults for data and logo")
    parser.add_argument("-o", "--output", default="qr.png", help="Output filename")
    parser.add_argument("-l", "--logo", help="Path to logo image to place in center")
    parser.add_argument("--logo-scale", type=float, default=0.312, help="Logo size as fraction of QR (0.0-0.5)")
    parser.add_argument("--box-size", type=int, default=10)
    parser.add_argument("--border", type=int, default=6)
    parser.add_argument("--autotune-min-ecc", type=float, default=0.15, help="Autotune: minimum ECC percent to keep (0-30). Default 0.15 (15%). Script will find largest logo scale that preserves at least this ECC")
    parser.add_argument("--no-autotune", action="store_true", help="Disable autotune even if --autotune-min-ecc is set; use provided --logo-scale instead")
    parser.add_argument("--autotune-start", type=float, default=0.05, help="Autotune start scale")
    parser.add_argument("--autotune-tol", type=float, default=0.01, help="Autotune tolerance (stopping criteria for binary search)")
    parser.add_argument("--autotune-max", type=float, default=0.6, help="Autotune max scale to try")

    args = parser.parse_args()

    # Ensure config exists; if not, create an example YAML config
    cfg_path = args.config
    if not os.path.exists(cfg_path):
        example = {"data": "myexampleurl", "logo": "myexamplelogo"}
        try:
            if yaml:
                with open(cfg_path, "w", encoding="utf-8") as f:
                    yaml.safe_dump(example, f)
            else:
                with open(cfg_path, "w", encoding="utf-8") as f:
                    f.write("data: myexampleurl\nlogo: myexamplelogo\n")
            print(f"Created example config at {cfg_path}. Edit it to set your defaults.")
        except Exception as e:
            print(f"Failed to create example config: {e}")

    # Load config if available
    cfg = {}
    if os.path.exists(cfg_path):
        try:
            if yaml:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
            else:
                # minimal YAML parsing fallback for simple key: value pairs
                with open(cfg_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if ":" in line:
                            k, v = line.split(":", 1)
                            cfg[k.strip()] = v.strip()
        except Exception:
            cfg = {}

    # Use config values unless overridden on CLI
    data_val = args.data
    if (not args.data or args.data == parser.get_default('data')) and cfg.get('data'):
        data_val = cfg.get('data')

    logo_val = args.logo
    if (not args.logo) and cfg.get('logo'):
        logo_val = cfg.get('logo')

    # Run autotune by default when --autotune-min-ecc is set, unless user opts out
    if args.autotune_min_ecc is not None and not args.no_autotune:
        if not args.logo:
            print("Autotune requires --logo path to be provided.")
        else:
            best = find_max_logo_scale(data_val, logo_val, args.output, start=args.autotune_start, tol=args.autotune_tol, max_scale=args.autotune_max, box_size=args.box_size, border=args.border, min_ecc_left=args.autotune_min_ecc)
            if best is None:
                print("No logo size found that satisfies the requested minimum ECC left.")
            else:
                print(f"Autotune found max logo scale: {best:.3f} (saved to {args.output})")
    else:
        make_qr(data_val, args.output, logo_val, args.logo_scale, args.box_size, args.border)