import io
import re
import argparse
import base64
import os
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


def make_sheet(contents: List[str], out_svg: str, out_pdf: str = None, cut_guides: bool = True):

    # A4 in mm
    A4_W = 210.0
    A4_H = 297.0
    margin = 10.0
    cols = 4
    rows = 5

    usable_w = A4_W - 2 * margin
    usable_h = A4_H - 2 * margin
    cell_size = min(usable_w / cols, usable_h / rows)

    fragments = []
    # Try to load local config for logo settings if available
    logo_path = None
    logo_scale = None
    cfg_path = 'qr_config.yaml'
    if os.path.exists(cfg_path):
        try:
            if yaml:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    cfg = yaml.safe_load(f) or {}
            else:
                # minimal fallback parsing
                cfg = {}
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if ':' in line:
                            k, v = line.split(':', 1)
                            cfg[k.strip()] = v.strip().strip('"\'')
        except Exception:
            cfg = {}

        if cfg.get('logo'):
            logo_path = cfg.get('logo')
        if cfg.get('logo_scale'):
            try:
                logo_scale = float(cfg.get('logo_scale'))
            except Exception:
                logo_scale = None

    # Use qrcode + Pillow to produce PNGs, then embed as data URIs in the SVG
    for c in contents:
        qr_img = make_qr_image(c, logo_path=logo_path, logo_scale=(logo_scale if logo_scale is not None else 0.312))
        buf = io.BytesIO()
        qr_img.save(buf, format='PNG')
        data = base64.b64encode(buf.getvalue()).decode('ascii')
        fragments.append(data)

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4_W}mm" height="{A4_H}mm" viewBox="0 0 {A4_W} {A4_H}">',
        f'<rect width="100%" height="100%" fill="#ffffff"/>',
    ]

    # Draw cut guides (dashed rectangles for each cell)
    if cut_guides:
        guide_stroke = 0.25  # mm
        dash = "2,2"
        for r in range(rows):
            for c in range(cols):
                gx = margin + c * cell_size
                gy = margin + r * cell_size
                svg_lines.append(
                    f'<rect x="{gx:.6f}" y="{gy:.6f}" width="{cell_size:.6f}" height="{cell_size:.6f}" fill="none" stroke="#000000" stroke-width="{guide_stroke}mm" stroke-dasharray="{dash}"/>'
                )

    for idx, data in enumerate(fragments):
        col = idx % cols
        row = idx // cols
        x_mm = margin + col * cell_size
        y_mm = margin + row * cell_size
        svg_lines.append(f'<image x="{x_mm:.6f}mm" y="{y_mm:.6f}mm" width="{cell_size:.6f}mm" height="{cell_size:.6f}mm" href="data:image/png;base64,{data}" preserveAspectRatio="xMidYMid meet"/>' )

    # Optional: small corner crop marks (outside each cell)
    if cut_guides:
        mark_len = min(7.0, cell_size * 0.2)
        mark_stroke = 0.4
        for r in range(rows):
            for c in range(cols):
                gx = margin + c * cell_size
                gy = margin + r * cell_size
                x2 = gx + cell_size
                y2 = gy + cell_size
                # top-left
                svg_lines.append(f'<line x1="{gx - mark_len:.6f}" y1="{gy:.6f}" x2="{gx + (mark_len*0.2):.6f}" y2="{gy:.6f}" stroke="#000" stroke-width="{mark_stroke}mm"/>')
                svg_lines.append(f'<line x1="{gx:.6f}" y1="{gy - mark_len:.6f}" x2="{gx:.6f}" y2="{gy + (mark_len*0.2):.6f}" stroke="#000" stroke-width="{mark_stroke}mm"/>')
                # top-right
                svg_lines.append(f'<line x1="{x2 - (mark_len*0.2):.6f}" y1="{gy:.6f}" x2="{x2 + mark_len:.6f}" y2="{gy:.6f}" stroke="#000" stroke-width="{mark_stroke}mm"/>')
                svg_lines.append(f'<line x1="{x2:.6f}" y1="{gy - mark_len:.6f}" x2="{x2:.6f}" y2="{gy + (mark_len*0.2):.6f}" stroke="#000" stroke-width="{mark_stroke}mm"/>')
                # bottom-left
                svg_lines.append(f'<line x1="{gx - mark_len:.6f}" y1="{y2:.6f}" x2="{gx + (mark_len*0.2):.6f}" y2="{y2:.6f}" stroke="#000" stroke-width="{mark_stroke}mm"/>')
                svg_lines.append(f'<line x1="{gx:.6f}" y1="{y2 - (mark_len*0.2):.6f}" x2="{gx:.6f}" y2="{y2 + mark_len:.6f}" stroke="#000" stroke-width="{mark_stroke}mm"/>')
                # bottom-right
                svg_lines.append(f'<line x1="{x2 - (mark_len*0.2):.6f}" y1="{y2:.6f}" x2="{x2 + mark_len:.6f}" y2="{y2:.6f}" stroke="#000" stroke-width="{mark_stroke}mm"/>')
                svg_lines.append(f'<line x1="{x2:.6f}" y1="{y2 - (mark_len*0.2):.6f}" x2="{x2:.6f}" y2="{y2 + mark_len:.6f}" stroke="#000" stroke-width="{mark_stroke}mm"/>')

    svg_lines.append('</svg>')
    svg_content = '\n'.join(svg_lines)

    with open(out_svg, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    if out_pdf:
        # Try cairosvg first, then fall back to Inkscape or ImageMagick if available
        try:
            import cairosvg

            cairosvg.svg2pdf(bytestring=svg_content.encode('utf-8'), write_to=out_pdf)
            print(f'PDF created: {out_pdf} (via cairosvg)')
        except Exception:
            import shutil
            import subprocess

            # prefer inkscape if present
            inkscape_cmd = shutil.which('inkscape') or shutil.which('inkscape.com')
            if inkscape_cmd:
                try:
                    subprocess.check_call([inkscape_cmd, out_svg, '--export-type=pdf', '--export-filename', out_pdf])
                    print(f'PDF created: {out_pdf} (via Inkscape)')
                except Exception as e:
                    print('Inkscape failed to convert SVG to PDF:', e)
            else:
                # try ImageMagick (magick) as last resort
                magick_cmd = shutil.which('magick')
                convert_cmd = shutil.which('convert')
                chosen_cmd = magick_cmd
                if not chosen_cmd and convert_cmd:
                    import os
                    # On Windows, C:\Windows\System32\convert.exe is the filesystem converter
                    # and NOT ImageMagick. Ignore that one to avoid accidental use.
                    convert_dir = os.path.normcase(os.path.dirname(convert_cmd))
                    if not convert_dir.endswith(os.path.normcase('\\windows\\system32')):
                        chosen_cmd = convert_cmd

                if chosen_cmd:
                    try:
                        # ImageMagick: `magick input.svg output.pdf` or `convert input.svg output.pdf`
                        subprocess.check_call([chosen_cmd, out_svg, out_pdf])
                        print(f'PDF created: {out_pdf} (via ImageMagick)')
                    except Exception as e:
                        print('ImageMagick failed to convert SVG to PDF:', e)
                else:
                    print('No SVG-to-PDF converter available; install cairosvg, Inkscape, or ImageMagick to enable PDF output')


def fill_template_with_qr(template_path: str, data: str, out_svg: str, logo_path: str = None, logo_scale: float = None):
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


def main():
    parser = argparse.ArgumentParser(description='Generate A4 SVG/PDF with 20 QR codes')
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--out-svg', default='qr_sheet.svg')
    parser.add_argument('--out-pdf', default='qr_sheet.pdf')
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
            logo_path = cfg.get('logo')
            try:
                logo_scale = float(cfg.get('logo_scale')) if cfg.get('logo_scale') else None
            except Exception:
                logo_scale = None
            # prefer config 'data' if contents look like defaults (e.g., 'QR-1') or empty
            cfg_data = cfg.get('data')
            if cfg_data and (not first or re.match(r'^QR-\d+$', first)):
                first = cfg_data

        fill_template_with_qr(args.template, first, args.out_svg, logo_path=logo_path, logo_scale=logo_scale)

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
        make_sheet(contents, args.out_svg, args.out_pdf if args.pdf else None)


if __name__ == '__main__':
    main()
