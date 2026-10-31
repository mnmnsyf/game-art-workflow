#!/usr/bin/env python3
"""Transparency check for sprites / cut-outs.

    python alpha_check.py chair.png --out review/

Reports: whether a real alpha channel exists, a painted-in checkerboard
("fake transparency"), opaque / semi / clear pixel ratios, light or dark halo
in the semi-transparent fringe, and the margin between the silhouette and the
canvas edge. Writes a black / white / magenta composite for visual review.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _imgutil import Image, default_out, flatten, labeled_row, luminance, open_image, utf8_stdout

BLOCKS = (4, 6, 8, 10, 12, 16, 20, 24, 32)


def detect_checkerboard(rgb: Image.Image) -> dict | None:
    """Look for a two-tone, low-saturation checker pattern along the borders."""
    w, h = rgb.size
    if w < 16 or h < 16:
        return None
    px = rgb.load()
    band = max(4, min(w, h) // 8)
    coords = [(x, y) for y in range(h) for x in range(w)
              if (x < band or y < band or x >= w - band or y >= h - band) and (x + y) % 2 == 0]
    if len(coords) > 40000:
        coords = coords[:: len(coords) // 40000 + 1]
    best = None
    for b in BLOCKS:
        groups = ([], [])
        sat_ok = 0
        for x, y in coords:
            c = px[x, y]
            if max(c) - min(c) <= 12:
                sat_ok += 1
            groups[((x // b) + (y // b)) % 2].append(luminance(c))
        if sat_ok / len(coords) < 0.8 or not groups[0] or not groups[1]:
            continue
        m0 = sum(groups[0]) / len(groups[0])
        m1 = sum(groups[1]) / len(groups[1])
        s0 = (sum((v - m0) ** 2 for v in groups[0]) / len(groups[0])) ** 0.5
        s1 = (sum((v - m1) ** 2 for v in groups[1]) / len(groups[1])) ** 0.5
        contrast = abs(m0 - m1)
        if contrast >= 12 and max(s0, s1) < contrast / 3:
            score = contrast / (max(s0, s1) + 1)
            if not best or score > best["score"]:
                best = {"block_px": b, "tones": [round(m0), round(m1)], "score": round(score, 1)}
    return best


def analyze(img: Image.Image, halo_light: int, halo_dark: int) -> dict:
    has_alpha = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
    rgba = img.convert("RGBA")
    w, h = rgba.size
    res = {"size": [w, h], "mode": img.mode, "has_alpha_channel": has_alpha, "issues": []}
    alpha = rgba.getchannel("A")
    hist = alpha.histogram()
    total = w * h
    clear, opaque = hist[0], hist[255]
    semi = total - clear - opaque
    res.update({
        "clear_ratio": round(clear / total, 4), "semi_ratio": round(semi / total, 4),
        "opaque_ratio": round(opaque / total, 4),
    })
    if not has_alpha or clear == 0:
        cb = detect_checkerboard(rgba.convert("RGB"))
        res["fake_checkerboard"] = cb
        if not has_alpha:
            res["issues"].append("no alpha channel")
        elif clear == 0:
            res["issues"].append("alpha is fully opaque; there is no transparent area")
        if cb:
            res["issues"].append(f"suspected checkerboard painted into RGB (cells ~{cb['block_px']}px, tones {cb['tones']}): this is fake transparency")
        return res

    bbox = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox:
        margin = {"left": bbox[0], "top": bbox[1], "right": w - bbox[2], "bottom": h - bbox[3]}
        res["bbox"] = list(bbox)
        res["margin_px"] = margin
        touching = [k for k, v in margin.items() if v == 0]
        if touching:
            res["issues"].append(f"silhouette touches the canvas edge ({', '.join(touching)}); it may be cut off or lack padding")
    else:
        res["issues"].append("image is fully transparent")
        return res

    px = rgba.load()
    light = dark = n = 0
    step = 1 if total <= 4_000_000 else 2
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b, a = px[x, y]
            if 0 < a < 255:
                n += 1
                lum = luminance((r, g, b))
                if lum >= halo_light:
                    light += 1
                elif lum <= halo_dark:
                    dark += 1
    if n:
        res["fringe_light_ratio"] = round(light / n, 3)
        res["fringe_dark_ratio"] = round(dark / n, 3)
        if light / n > 0.35:
            res["issues"].append(f"{light / n:.0%} of the semi-transparent fringe is light; a white halo will show on dark backgrounds")
        if dark / n > 0.35:
            res["issues"].append(f"{dark / n:.0%} of the semi-transparent fringe is dark; a dark halo will show on light backgrounds")
    elif semi == 0:
        res["note"] = "only fully clear and fully opaque pixels (hard edge); fine for pixel art, may look jagged for painted art"
    return res


def main(argv=None) -> int:
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("images", nargs="+")
    p.add_argument("--out", help="output directory for composites")
    p.add_argument("--halo-light", type=int, default=225)
    p.add_argument("--halo-dark", type=int, default=30)
    p.add_argument("--expect-size", help="required WxH, e.g. 64x64")
    p.add_argument("--max-colors", type=int, help="max distinct visible colours (palette budget for pixel art)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    results, failed = [], False
    for path in a.images:
        src = Path(path)
        img = open_image(src)
        r = analyze(img, a.halo_light, a.halo_dark)
        if a.expect_size:
            ew, eh = (int(v) for v in a.expect_size.lower().split("x"))
            if tuple(img.size) != (ew, eh):
                r["issues"].append(f"size {img.size[0]}x{img.size[1]} does not match the expected {ew}x{eh}")
        if a.max_colors:
            rgba = img.convert("RGBA")
            visible = {c[:3] for c in rgba.getdata() if c[3] > 0}
            r["visible_colors"] = len(visible)
            if len(visible) > a.max_colors:
                r["issues"].append(f"{len(visible)} distinct visible colours exceed the palette budget of {a.max_colors}")
        r["file"] = str(src.resolve())
        view = img.convert("RGBA")
        if max(view.size) > 512:
            f = 512 / max(view.size)
            view = view.resize((max(1, int(view.width * f)), max(1, int(view.height * f))), Image.Resampling.LANCZOS)
        elif max(view.size) < 128:
            k = 128 // max(view.size)
            view = view.resize((view.width * k, view.height * k), Image.Resampling.NEAREST)
        comps = [flatten(view, c) for c in ((0, 0, 0), (255, 255, 255), (255, 0, 255))]
        out_dir = a.out if a.out is None or Path(a.out).suffix == "" else str(Path(a.out).parent)
        out = default_out(src, "alpha", out_dir)
        labeled_row(comps, ["black", "white", "magenta"]).save(out)
        r["composite"] = str(out.resolve())
        r["pass"] = not r["issues"]
        failed |= bool(r["issues"])
        results.append(r)

    if a.json:
        print(json.dumps(results if len(results) > 1 else results[0], ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"{Path(r['file']).name} {r['size'][0]}×{r['size'][1]} mode={r['mode']}")
            print(f"  clear {r['clear_ratio']:.1%}  semi {r['semi_ratio']:.1%}  opaque {r['opaque_ratio']:.1%}")
            if "margin_px" in r:
                print(f"  edge margin {r['margin_px']}")
            if "fringe_light_ratio" in r:
                print(f"  semi-transparent fringe: light {r['fringe_light_ratio']:.0%} dark {r['fringe_dark_ratio']:.0%}")
            if r.get("note"):
                print(f"  note: {r['note']}")
            for i in r["issues"]:
                print(f"  WARNING: {i}")
            print(f"  {'technical check passed (still inspect the composites)' if r['pass'] else 'failed; fix before sending for review'}")
            print(f"  composite: {r['composite']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
