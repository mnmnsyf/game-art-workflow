#!/usr/bin/env python3
"""Decoded pixel comparison between two images.

    python compare_images.py source.png imported.png --out review/

Use it to prove a conversion is lossless (max diff 0), to quantify drift, or
to make a labelled before/after/diff strip for rework reviews. File hashes are
reported too: identical bytes prove identity, different bytes do not prove a
visual change (re-encoding changes bytes).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from _imgutil import Image, checker, flatten, labeled_row, open_image, utf8_stdout
from PIL import ImageChops


def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def compare(a: Image.Image, b: Image.Image, threshold: int) -> tuple[dict, Image.Image]:
    mode = "RGBA" if "A" in a.getbands() or "A" in b.getbands() else "RGB"
    a, b = a.convert(mode), b.convert(mode)
    diff = ImageChops.difference(a, b)
    bands = diff.split()
    max_diff = max(band.getextrema()[1] for band in bands)
    total = a.width * a.height
    sq = 0.0
    abs_sum = 0.0
    for band in bands:
        hist = band.histogram()
        abs_sum += sum(v * c for v, c in enumerate(hist))
        sq += sum(v * v * c for v, c in enumerate(hist))
    n = total * len(bands)
    mse = sq / n
    per_pixel = bands[0]
    for band in bands[1:]:
        per_pixel = ImageChops.lighter(per_pixel, band)
    changed = sum(c for v, c in enumerate(per_pixel.histogram()) if v > threshold)
    stats = {
        "mode": mode, "max_diff": max_diff, "mean_abs_diff": round(abs_sum / n, 4),
        "psnr_db": None if mse == 0 else round(10 * math.log10(255 ** 2 / mse), 2),
        "changed_pixel_ratio": round(changed / total, 6), "threshold": threshold,
    }
    heat = per_pixel.point(lambda v: 0 if v <= threshold else min(255, 64 + v * 4))
    heat = Image.merge("RGB", (heat, heat.point(lambda v: v // 3), Image.new("L", heat.size, 0)))
    return stats, heat


def main(argv=None) -> int:
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("a", help="baseline (original / old version)")
    p.add_argument("b", help="comparison (imported / new version)")
    p.add_argument("--out", help="output file or directory for the side-by-side strip")
    p.add_argument("--labels", nargs=2, default=["A baseline", "B compared"])
    p.add_argument("--threshold", type=int, default=0, help="per-pixel difference <= this counts as identical")
    p.add_argument("--resize", action="store_true", help="when sizes differ, resize B to A before comparing")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    pa, pb = Path(a.a), Path(a.b)
    ia, ib = open_image(pa), open_image(pb)
    res = {"a": str(pa.resolve()), "b": str(pb.resolve()), "size_a": list(ia.size), "size_b": list(ib.size)}
    ha, hb = file_hash(pa), file_hash(pb)
    res["bytes_identical"] = ha == hb
    if ia.size != ib.size:
        if not a.resize:
            res["error"] = "sizes differ; add --resize to compare after scaling (indicative only)"
            print(json.dumps(res, ensure_ascii=False, indent=2) if a.json else f"WARNING: {res['error']}: {ia.size} vs {ib.size}")
            return 2
        ib = ib.resize(ia.size, Image.Resampling.LANCZOS)
        res["resized_b"] = True
    stats, heat = compare(ia, ib, a.threshold)
    res.update(stats)
    res["pixel_identical"] = stats["max_diff"] <= a.threshold

    out = None
    if a.out is not None:
        o = Path(a.out)
        if o.suffix:
            o.parent.mkdir(parents=True, exist_ok=True)
            out = o
        else:
            o.mkdir(parents=True, exist_ok=True)
            out = o / f"{pa.stem}_vs_{pb.stem}.png"
        views = [ia.convert("RGBA"), ib.convert("RGBA"), heat]
        if max(ia.size) > 640:
            f = 640 / max(ia.size)
            size = (max(1, int(ia.width * f)), max(1, int(ia.height * f)))
            views = [v.resize(size, Image.Resampling.LANCZOS) for v in views]
        views = [flatten(v, checker(v.size)) if v.mode == "RGBA" else v for v in views]
        labeled_row(views, [a.labels[0], a.labels[1], "diff"]).save(out)
        res["strip"] = str(out.resolve())

    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"{pa.name} vs {pb.name}  {ia.size[0]}×{ia.size[1]}")
        print(f"  bytes identical: {'yes' if res['bytes_identical'] else 'no'}")
        print(f"  max diff {stats['max_diff']}  mean diff {stats['mean_abs_diff']}  PSNR {stats['psnr_db'] or 'inf'} dB")
        print(f"  changed pixels {stats['changed_pixel_ratio']:.4%} (threshold {a.threshold})")
        print(f"  verdict: {'pixel-identical' if res['pixel_identical'] else 'differs'}")
        if out:
            print(f"  strip: {res['strip']}")
    return 0 if res["pixel_identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
