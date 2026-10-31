#!/usr/bin/env python3
"""Numbered contact sheet for reviewing candidates or a batch at once.

    python contact_sheet.py review/cand_*.png --out review/sheet.png
    python contact_sheet.py batch/*.png --anchor style/anchor1.png --cols 4

Transparent images are shown over a checkerboard. Anchor images (approved
style references) are placed first and tagged so new work can be judged
against them side by side.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

from _imgutil import Image, ImageDraw, checker, flatten, font, open_image, utf8_stdout


def expand(patterns: list[str]) -> list[Path]:
    out = []
    for pat in patterns:
        hits = sorted(glob.glob(pat))
        out.extend(Path(h) for h in (hits or [pat]))
    return out


def main(argv=None) -> int:
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("images", nargs="+")
    p.add_argument("--anchor", nargs="*", default=[], help="approved style anchor images")
    p.add_argument("--out", default="contact_sheet.png")
    p.add_argument("--cols", type=int, default=0, help="columns; 0 = auto")
    p.add_argument("--cell", type=int, default=320, help="cell size in px")
    p.add_argument("--title")
    p.add_argument("--pixel-art", action="store_true", help="use Nearest when upscaling to keep pixels crisp")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    items = [(path, True) for path in expand(a.anchor)] + [(path, False) for path in expand(a.images)]
    if not items:
        p.error("no input images")
    n = len(items)
    cols = a.cols or min(n, 4 if n > 4 else n)
    rows = (n + cols - 1) // cols
    cell, pad, label_h = a.cell, 12, 40
    title_h = 36 if a.title else 0
    W = cols * cell + (cols + 1) * pad
    H = title_h + rows * (cell + label_h) + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), (28, 28, 32))
    d = ImageDraw.Draw(sheet)
    f, fs = font(16), font(12)
    if a.title:
        d.text((pad, 8), a.title, fill=(240, 240, 240), font=font(20))

    index = []
    k = 0
    for i, (path, is_anchor) in enumerate(items):
        img = open_image(path).convert("RGBA")
        scale = min(cell / img.width, cell / img.height)
        resample = Image.Resampling.NEAREST if (a.pixel_art and scale >= 1) else Image.Resampling.LANCZOS
        thumb = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), resample)
        thumb = flatten(thumb, checker(thumb.size, 8, (70, 70, 74), (90, 90, 96)))
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad)
        y = title_h + pad + r * (cell + label_h + pad)
        sheet.paste(thumb, (x + (cell - thumb.width) // 2, y + (cell - thumb.height) // 2))
        if is_anchor:
            tag = "ANCHOR"
            d.rectangle([x - 3, y - 3, x + cell + 2, y + cell + 2], outline=(230, 180, 60), width=3)
        else:
            k += 1
            tag = f"#{k}"
        d.text((x, y + cell + 4), f"{tag}  {img.width}×{img.height}", fill=(240, 240, 240), font=f)
        d.text((x, y + cell + 22), path.name[:40], fill=(160, 160, 170), font=fs)
        index.append({"tag": tag, "file": str(path.resolve()), "size": [img.width, img.height]})

    out = Path(a.out)
    if not out.suffix:
        out.mkdir(parents=True, exist_ok=True)
        out = out / "contact_sheet.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    if a.json:
        print(json.dumps({"sheet": str(out.resolve()), "items": index}, ensure_ascii=False, indent=2))
    else:
        for it in index:
            print(f"{it['tag']:<5} {it['file']}")
        print(f"contact sheet: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
