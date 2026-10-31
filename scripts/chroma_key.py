#!/usr/bin/env python3
"""Remove a solid generation background and decontaminate the edge fringe.

    python chroma_key.py raw/barrel.png -o work/barrel.png
    python chroma_key.py raw/sheet.png -o work/sheet.png --bg "#FF00FF" --tolerance 60

Generators cannot be trusted to emit real alpha (asking for "transparent"
usually paints a checkerboard), so prompt a solid background and key it here.
Pixels within --tolerance of the background colour become clear, pixels
beyond --tolerance + --softness stay opaque, and the band between gets
partial alpha. Despill un-mixes the background colour from that band so a
magenta or green halo does not survive on other backgrounds. Run
alpha_check.py on the result before review.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _imgutil import Image, default_out, open_image, utf8_stdout


def parse_hex(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    if len(v) != 6:
        raise argparse.ArgumentTypeError(f"expected #RRGGBB, got {value!r}")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def border_color(rgb: Image.Image) -> tuple[tuple[int, int, int], float]:
    """Median border colour and the share of border pixels close to it."""
    w, h = rgb.size
    px = rgb.load()
    pts = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
    pts += [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    cols = [px[p] for p in pts]
    med = tuple(sorted(c[i] for c in cols)[len(cols) // 2] for i in range(3))
    near = sum(1 for c in cols if dist(c, med) <= 30) / len(cols)
    return med, near


def dist(a, b) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def key(img: Image.Image, bg, tol: float, soft: float, despill: bool) -> tuple[Image.Image, dict]:
    rgb = img.convert("RGB")
    w, h = rgb.size
    src = rgb.load()
    out = Image.new("RGBA", (w, h))
    dst = out.load()
    clear = partial = 0
    for y in range(h):
        for x in range(w):
            c = src[x, y]
            d = dist(c, bg)
            if d <= tol:
                dst[x, y] = (0, 0, 0, 0)
                clear += 1
                continue
            a = 1.0 if d >= tol + soft else (d - tol) / soft
            if a < 1.0:
                partial += 1
                if despill:
                    # observed = a*fg + (1-a)*bg  ->  fg = (observed - (1-a)*bg) / a
                    c = tuple(max(0, min(255, round((c[i] - (1 - a) * bg[i]) / a))) for i in range(3))
            dst[x, y] = (*c, round(a * 255))
    total = w * h
    return out, {"clear_ratio": round(clear / total, 4), "partial_ratio": round(partial / total, 4)}


def main(argv=None) -> int:
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("image")
    p.add_argument("-o", "--out", help="output file or directory (default: <name>_keyed.png beside the input)")
    p.add_argument("--bg", type=parse_hex, help="background colour #RRGGBB (default: median border colour)")
    p.add_argument("--tolerance", type=float, default=40, help="RGB distance that becomes fully clear")
    p.add_argument("--softness", type=float, default=50, help="width of the partial-alpha band beyond tolerance")
    p.add_argument("--no-despill", action="store_true", help="keep the original colour in the partial band")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    src = Path(a.image)
    img = open_image(src)
    detected, border_share = border_color(img.convert("RGB"))
    bg = a.bg or detected
    out_img, stats = key(img, bg, a.tolerance, a.softness, not a.no_despill)
    out = default_out(src, "keyed", a.out)
    out_img.save(out)

    issues = []
    if border_share < 0.9:
        issues.append(f"only {border_share:.0%} of the border matches the background; the subject may touch the edge or the background is not solid")
    if stats["clear_ratio"] < 0.05:
        issues.append("almost nothing was keyed; check --bg or regenerate on a solid background")
    if stats["partial_ratio"] > 0.15:
        issues.append("a large partial-alpha band; the background colour is probably too close to the subject — regenerate with a more distinct colour")

    res = {"input": str(src.resolve()), "output": str(out.resolve()), "bg": "#%02X%02X%02X" % tuple(bg),
           "border_match": round(border_share, 3), **stats, "issues": issues, "pass": not issues}
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"{src.name}: background {res['bg']} (border match {border_share:.0%})")
        print(f"  clear {stats['clear_ratio']:.1%}  partial {stats['partial_ratio']:.1%}")
        for i in issues:
            print(f"  WARNING: {i}")
        print(f"  output: {res['output']}  — run alpha_check.py on it before review")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
