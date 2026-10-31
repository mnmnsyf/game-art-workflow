#!/usr/bin/env python3
"""Slice a generated sheet / prop pack into aligned, equally scaled PNGs.

    python grid_slice.py work/props_keyed.png --grid 3x3 -o work/props/ --names "rock,crate,lamp,..."
    python grid_slice.py work/frames_keyed.png --grid 2x2 -o work/idle/ --align feet --cell 256

Input should already have real alpha (run chroma_key.py first). Each cell is
trimmed to its visible pixels, all cells share ONE scale factor (so relative
sizes survive), and each is placed on a fixed canvas with a common anchor:
feet/bottom-center (default), center, or bottom-left. Cells whose content
touches the cell border are flagged — that usually means something was cut
off and the object should be regenerated on its own, not forced through.
Writes <out>/slices.json with bbox, anchor, and flags per cell.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _imgutil import Image, open_image, utf8_stdout


def parse_grid(value: str) -> tuple[int, int]:
    try:
        r, c = value.lower().split("x")
        return int(r), int(c)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected ROWSxCOLS, got {value!r}")


def main(argv=None) -> int:
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("image")
    p.add_argument("--grid", type=parse_grid, required=True, help="ROWSxCOLS, e.g. 3x3")
    p.add_argument("-o", "--out", required=True, help="output directory")
    p.add_argument("--names", help="comma-separated names in row-major order (default: cell_RC)")
    p.add_argument("--cell", type=int, default=0, help="output canvas size in px (default: fit the largest object)")
    p.add_argument("--padding", type=int, default=8, help="transparent padding inside the output canvas")
    p.add_argument("--align", choices=["feet", "center", "bottom-left"], default="feet")
    p.add_argument("--edge-margin", type=int, default=2, help="content within this many px of a cell edge is flagged")
    p.add_argument("--alpha-threshold", type=int, default=8)
    p.add_argument("--pixel-art", action="store_true", help="scale with Nearest and only by whole factors")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    img = open_image(a.image).convert("RGBA")
    rows, cols = a.grid
    cw, ch = img.width // cols, img.height // rows
    names = [n.strip() for n in a.names.split(",")] if a.names else []
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    cells = []
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            box = (c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)
            cell = img.crop(box)
            mask = cell.getchannel("A").point(lambda v: 255 if v > a.alpha_threshold else 0)
            bbox = mask.getbbox()
            name = names[i] if i < len(names) and names[i] else f"cell_{r}{c}"
            flags = []
            if not bbox:
                flags.append("empty")
            else:
                m = a.edge_margin
                if bbox[0] <= m or bbox[1] <= m or bbox[2] >= cw - m or bbox[3] >= ch - m:
                    flags.append("touches_cell_edge")
            cells.append({"name": name, "row": r, "col": c, "cell_box": list(box),
                          "bbox": list(bbox) if bbox else None, "flags": flags, "img": cell})

    live = [x for x in cells if x["bbox"]]
    if not live:
        print("error: every cell is empty (is the input keyed?)")
        return 2
    max_w = max(x["bbox"][2] - x["bbox"][0] for x in live)
    max_h = max(x["bbox"][3] - x["bbox"][1] for x in live)
    canvas = a.cell or (max(max_w, max_h) + 2 * a.padding)
    inner = canvas - 2 * a.padding
    scale = min(inner / max_w, inner / max_h)
    if a.pixel_art:
        scale = max(1, int(scale)) if scale >= 1 else 1 / max(1, round(1 / scale))
    resample = Image.Resampling.NEAREST if a.pixel_art else Image.Resampling.LANCZOS

    for x in cells:
        x.pop("img_out", None)
        if not x["bbox"]:
            continue
        obj = x["img"].crop(x["bbox"])
        size = (max(1, round(obj.width * scale)), max(1, round(obj.height * scale)))
        obj = obj.resize(size, resample) if size != obj.size else obj
        out = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
        if a.align == "center":
            pos = ((canvas - obj.width) // 2, (canvas - obj.height) // 2)
        elif a.align == "bottom-left":
            pos = (a.padding, canvas - a.padding - obj.height)
        else:
            pos = ((canvas - obj.width) // 2, canvas - a.padding - obj.height)
        out.alpha_composite(obj, pos)
        path = out_dir / f"{x['name']}.png"
        out.save(path)
        anchor = {"feet": (canvas // 2, canvas - a.padding), "center": (canvas // 2, canvas // 2),
                  "bottom-left": (a.padding, canvas - a.padding)}[a.align]
        x.update({"file": str(path.resolve()), "size": [canvas, canvas], "anchor_px": list(anchor),
                  "content_px": list(size)})

    for x in cells:
        x.pop("img")
    report = {"source": str(Path(a.image).resolve()), "grid": f"{rows}x{cols}", "cell_px": [cw, ch],
              "canvas_px": canvas, "scale": round(scale, 4), "align": a.align, "cells": cells}
    (out_dir / "slices.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    flagged = [x for x in cells if x["flags"]]
    if a.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{rows}x{cols} sheet, cell {cw}x{ch}px -> {canvas}px canvas, shared scale {scale:.3f}, align {a.align}")
        for x in cells:
            print(f"  {x['name']:<16} {'OK' if not x['flags'] else 'FLAG: ' + ', '.join(x['flags'])}")
        if flagged:
            print("  WARNING: flagged cells were cut off or empty; regenerate them individually instead of relaxing the check")
        print(f"  manifest: {(out_dir / 'slices.json').resolve()}")
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
