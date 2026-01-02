import io
import re
import argparse
import base64
import os
import sys
from typing import List

try:
    import yaml
except Exception:
    yaml = None

from qrcode_plain import make_qr_image


def parse_viewbox(svg_text: str):
    m = re.search(r'viewBox\s*=\s*"([0-9. ]+)"', svg_text)
    if m:
        parts = [float(x) for x in m.group(1).split()]
        if len(parts) == 4:
            return parts[2], parts[3]
    m = re.search(r'width\s*=\s*"([0-9.]+)', svg_text)
    n = re.search(r'height\s*=\s*"([0-9.]+)', svg_text)
    if m and n:
        return float(m.group(1)), float(n.group(1))
    return None, None


def strip_outer_svg(svg_text: str):
    start = svg_text.find('>')
    end = svg_text.rfind('</svg>')
    if start != -1 and end != -1:
        return svg_text[start+1:end]
    return svg_text


# Note: sheet generation has been removed. This script now supports only template
# filling via `--template`. The previous `make_sheet` implementation was intentionally
# discarded to simplify the tool and ensure template-only behavior.


def fill_template_with_qr(template_path: str, data: str, out_svg: str, logo_path: str = None, logo_scale: float = None, out_png: str = None):
    """Replace the element with id="placeholder" in `template_path` with an embedded PNG QR image.

    The placeholder is typically a <rect> inside a reusable group; replacing it in the group
    will populate every <use> instance in the template.
    """
    with open(template_path, 'r', encoding='utf-8') as f:
        svg_text = f.read()

    # find the element that contains id="placeholder" (self-closing or not)
    m = re.search(r'<([a-zA-Z0-9:_-]+)([^>]*)\s+id\s*=\s*"placeholder"([^>]*)\/?>', svg_text, re.IGNORECASE | re.DOTALL)
    if not m:
        raise RuntimeError('No element with id="placeholder" found in template')

    full_tag = m.group(0)

    def find_attr(tagtext, name):
        mm = re.search(rf'{name}\s*=\s*"([\-0-9.]+)"', tagtext)
        return mm.group(1) if mm else None

    x = find_attr(full_tag, 'x')
    y = find_attr(full_tag, 'y')
    w = find_attr(full_tag, 'width')
    h = find_attr(full_tag, 'height')

    # generate QR image PNG bytes
    qr_img = make_qr_image(data, logo_path=logo_path, logo_scale=logo_scale if logo_scale is not None else 0.312)
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')

    # If requested, write the single QR PNG to disk (the one embedded in the template)
    if out_png:
        try:
            qr_img.save(out_png, format='PNG')
            print(f'Single QR PNG saved: {out_png}')
        except Exception as e:
            print(f'Failed to save single QR PNG {out_png}: {e}')

    coord_attrs = []
    if x is not None:
        coord_attrs.append(f'x="{x}"')
    if y is not None:
        coord_attrs.append(f'y="{y}"')
    if w is not None:
        coord_attrs.append(f'width="{w}"')
    if h is not None:
        coord_attrs.append(f'height="{h}"')

    image_tag = '<image ' + ' '.join(coord_attrs) + f' href="data:image/png;base64,{b64}" preserveAspectRatio="xMidYMid meet"/>'

    new_svg = svg_text.replace(full_tag, image_tag, 1)

    with open(out_svg, 'w', encoding='utf-8') as f:
        f.write(new_svg)

    print(f'Template filled: {out_svg}')

    # Note: single QR PNG is already written earlier (via `out_png` param using `make_qr_image`).


def main():
    parser = argparse.ArgumentParser(description='Generate A4 SVG/PDF with 20 QR codes')
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--out-svg', default='qr_sheet.svg')
    parser.add_argument('--out-pdf', default='qr_sheet.pdf')
    parser.add_argument('--out-png', default=None, help='Write single QR PNG when using --template (path)')
    parser.add_argument('--no-pdf', dest='pdf', action='store_false')
    parser.add_argument('--from-file', help='Read one content per line from file')
    parser.add_argument('--template', help='Path to an SVG template to fill (replaces id="placeholder")')
    args = parser.parse_args()

    if args.from_file:
        with open(args.from_file, 'r', encoding='utf-8') as fh:
            contents = [line.strip() for line in fh if line.strip()][: args.count]
    else:
        contents = [f'QR-{i+1}' for i in range(args.count)]

    if args.template:
        # fill the provided template with the first content (prefer config data when present)
        first = contents[0] if contents else ''
        # try to read logo config if present
        cfg_path = 'qr_config.yaml'
        logo_path = None
        logo_scale = None
        if os.path.exists(cfg_path):
            try:
                if yaml:
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        cfg = yaml.safe_load(f) or {}
                else:
                    cfg = {}
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if ':' in line:
                                k, v = line.split(':', 1)
                                cfg[k.strip()] = v.strip().strip('"\'')
            except Exception:
                cfg = {}

            # assign logo path from config if present
            logo_path = cfg.get('logo')
            try:
                logo_scale = float(cfg.get('logo_scale')) if cfg.get('logo_scale') else None
            except Exception:
                logo_scale = None
            # prefer config 'data' if contents look like defaults (e.g., 'QR-1') or empty
            cfg_data = cfg.get('data')
            if cfg_data and (not first or re.match(r'^QR-\d+$', first)):
                first = cfg_data

        # Determine outputs from config `output` base name when not overridden on CLI.
        out_png = args.out_png
        cfg_out = None
        try:
            cfg_out = cfg.get('output')
        except Exception:
            cfg_out = None

        if cfg_out:
            base = os.path.splitext(os.path.basename(cfg_out))[0]

            # If caller didn't pass --out-svg (either `--out-svg value` or `--out-svg=value`), set to /output/<base>.svg (or local ./output)
            if not any(s.startswith('--out-svg') for s in sys.argv):
                if os.path.exists('/output'):
                    args.out_svg = f'/output/{base}.svg'
                else:
                    args.out_svg = os.path.join(os.getcwd(), 'output', f'{base}.svg')

            # If PDF output requested and caller didn't pass --out-pdf, set default
            if args.pdf and (not any(s.startswith('--out-pdf') for s in sys.argv)):
                if os.path.exists('/output'):
                    args.out_pdf = f'/output/{base}.pdf'
                else:
                    args.out_pdf = os.path.join(os.getcwd(), 'output', f'{base}.pdf')

            # Single PNG: prefer CLI --out-png; else set to /output/<base>.png
            if not out_png:
                if os.path.exists('/output'):
                    out_png = f'/output/{base}.png'
                else:
                    out_png = os.path.join(os.getcwd(), 'output', f'{base}.png')

        fill_template_with_qr(args.template, first, args.out_svg, logo_path=logo_path, logo_scale=logo_scale, out_png=out_png)

        if args.pdf and args.out_pdf:
            # convert to PDF using same fallback logic as make_sheet
            try:
                import cairosvg

                with open(args.out_svg, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                cairosvg.svg2pdf(bytestring=svg_content.encode('utf-8'), write_to=args.out_pdf)
                print(f'PDF created: {args.out_pdf} (via cairosvg)')
            except Exception:
                import shutil
                import subprocess

                inkscape_cmd = shutil.which('inkscape') or shutil.which('inkscape.com')
                if inkscape_cmd:
                    try:
                        subprocess.check_call([inkscape_cmd, args.out_svg, '--export-type=pdf', '--export-filename', args.out_pdf])
                        print(f'PDF created: {args.out_pdf} (via Inkscape)')
                    except Exception as e:
                        print('Inkscape failed to convert SVG to PDF:', e)
                else:
                    magick_cmd = shutil.which('magick')
                    convert_cmd = shutil.which('convert')
                    chosen_cmd = magick_cmd
                    if not chosen_cmd and convert_cmd:
                        convert_dir = os.path.normcase(os.path.dirname(convert_cmd))
                        if not convert_dir.endswith(os.path.normcase('\\windows\\system32')):
                            chosen_cmd = convert_cmd

                    if chosen_cmd:
                        try:
                            subprocess.check_call([chosen_cmd, args.out_svg, args.out_pdf])
                            print(f'PDF created: {args.out_pdf} (via ImageMagick)')
                        except Exception as e:
                            print('ImageMagick failed to convert SVG to PDF:', e)
                    else:
                        print('No SVG-to-PDF converter available; install cairosvg, Inkscape, or ImageMagick to enable PDF output')
    else:
        print("This script only supports --template mode. Provide --template with a template SVG to fill.")
        sys.exit(2)


if __name__ == '__main__':
    main()
