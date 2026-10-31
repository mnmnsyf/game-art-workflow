#!/usr/bin/env python3
"""N×N tiling preview plus seam and gradient metrics for a tileable texture.

    python tile_preview.py grass.png --grid 3 --out review/

Seam ratio = mean |edge column/row difference across the wrap| divided by the
mean difference between adjacent interior columns/rows. ~1.0 means the wrap
is as smooth as the texture itself; values well above ~1.5 usually show as a
visible seam. Gradient = luminance range of a 4×4 block average, in 0-255; a
large value repeats as visible banding.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _imgutil import Image, default_out, open_image, utf8_stdout


def _col_diff(px, w, h, x0, x1) -> float:
    total = 0.0
    for y in range(h):
        a, b = px[x0, y], px[x1, y]
        total += sum(abs(a[c] - b[c]) for c in range(3)) / 3
    return total / h


def _row_diff(px, w, h, y0, y1) -> float:
    total = 0.0
    for x in range(w):
        a, b = px[x, y0], px[x, y1]
        total += sum(abs(a[c] - b[c]) for c in range(3)) / 3
    return total / w


def seam_metrics(img: Image.Image) -> dict:
    rgb = img.convert("RGB")
    # Large textures: measure on a downsample to keep it quick but faithful.
    if max(rgb.size) > 1024:
        rgb = rgb.resize((rgb.width // 2, rgb.height // 2), Image.Resampling.BOX)
    w, h = rgb.size
    px = rgb.load()
    samples = max(1, min(32, w - 2))
    xs = [1 + i * (w - 2) // samples for i in range(samples)]
    base_x = sum(_col_diff(px, w, h, x, x - 1) for x in xs) / len(xs)
    ys = [1 + i * (h - 2) // samples for i in range(samples)]
    base_y = sum(_row_diff(px, w, h, y, y - 1) for y in ys) / len(ys)
    seam_x = _col_diff(px, w, h, w - 1, 0)
    seam_y = _row_diff(px, w, h, h - 1, 0)
    small = rgb.convert("L").resize((4, 4), Image.Resampling.BOX)
    vals = list(small.getdata())
    eps = 0.5
    return {
        "size": list(img.size),
        "seam_x": round(seam_x, 2), "baseline_x": round(base_x, 2),
        "seam_ratio_x": round(seam_x / max(base_x, eps), 2),
        "seam_y": round(seam_y, 2), "baseline_y": round(base_y, 2),
        "seam_ratio_y": round(seam_y / max(base_y, eps), 2),
        "gradient_range": int(max(vals) - min(vals)),
    }


def verdict(m: dict, ratio_limit: float, grad_limit: int) -> list[str]:
    issues = []
    if m["seam_ratio_x"] > ratio_limit:
        issues.append(f"visible left/right seam (ratio {m['seam_ratio_x']} > {ratio_limit})")
    if m["seam_ratio_y"] > ratio_limit:
        issues.append(f"visible top/bottom seam (ratio {m['seam_ratio_y']} > {ratio_limit})")
    if m["gradient_range"] > grad_limit:
        issues.append(f"low-frequency brightness gradient {m['gradient_range']} > {grad_limit}; repeats will show light/dark banding")
    return issues


def main(argv=None) -> int:
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("image")
    p.add_argument("--grid", type=int, default=3)
    p.add_argument("--scale", type=int, default=0, help="preview scale factor (Nearest, for pixel art); 0 = auto")
    p.add_argument("--out", help="output file or directory")
    p.add_argument("--ratio-limit", type=float, default=1.6)
    p.add_argument("--gradient-limit", type=int, default=24)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    src = Path(a.image)
    img = open_image(src)
    m = seam_metrics(img)
    issues = verdict(m, a.ratio_limit, a.gradient_limit)

    tile = img.convert("RGBA")
    scale = a.scale or (max(1, 384 // max(tile.size)) if max(tile.size) < 384 else 1)
    if scale > 1:
        tile = tile.resize((tile.width * scale, tile.height * scale), Image.Resampling.NEAREST)
    max_side = 2048
    if tile.width * a.grid > max_side:
        f = max_side / (tile.width * a.grid)
        tile = tile.resize((max(1, int(tile.width * f)), max(1, int(tile.height * f))), Image.Resampling.LANCZOS)
    sheet = Image.new("RGBA", (tile.width * a.grid, tile.height * a.grid))
    for gy in range(a.grid):
        for gx in range(a.grid):
            sheet.paste(tile, (gx * tile.width, gy * tile.height))
    out = default_out(src, f"tile{a.grid}x{a.grid}", a.out)
    sheet.save(out)

    m.update({"preview": str(out.resolve()), "issues": issues, "pass": not issues})
    if a.json:
        print(json.dumps(m, ensure_ascii=False, indent=2))
    else:
        print(f"{src.name} {m['size'][0]}×{m['size'][1]}")
        print(f"  left/right seam {m['seam_x']} (interior baseline {m['baseline_x']}, ratio {m['seam_ratio_x']})")
        print(f"  top/bottom seam {m['seam_y']} (interior baseline {m['baseline_y']}, ratio {m['seam_ratio_y']})")
        print(f"  low-frequency brightness gradient {m['gradient_range']}")
        for i in issues:
            print(f"  WARNING: {i}")
        print(f"  {'technical check passed (still review repeating features visually at actual UV scale)' if not issues else 'fix before sending for review'}")
        print(f"  preview: {out.resolve()}")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
