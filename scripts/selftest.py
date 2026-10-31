#!/usr/bin/env python3
"""Self-test for the bundled scripts using synthetic images in a temp dir.

    python selftest.py

Proves the scripts behave as documented; says nothing about art quality.
"""
from __future__ import annotations

import json
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
results: list[tuple[str, bool, str]] = []


def run(script: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([PY, str(HERE / script), *args], capture_output=True, text=True,
                          encoding="utf-8", cwd=cwd)


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def make_images(d: Path) -> dict:
    from PIL import Image, ImageDraw, ImageFilter
    rnd = random.Random(7)
    w = h = 64
    seamless = Image.new("RGB", (w, h))
    px = seamless.load()
    for y in range(h):
        for x in range(w):
            v = 120 + 40 * math.sin(2 * math.pi * x / w * 3) * math.cos(2 * math.pi * y / h * 2)
            n = rnd.randint(-6, 6)
            px[x, y] = (int(v * 0.6) + n, int(v) + n, int(v * 0.4) + n)
    seamless.save(d / "seamless.png")

    seamed = Image.new("RGB", (w, h))
    px = seamed.load()
    for y in range(h):
        for x in range(w):
            v = 40 + x * 3
            px[x, y] = (v // 2, v, v // 3)
    seamed.save(d / "seamed.png")

    fake = Image.new("RGB", (96, 96), (255, 255, 255))
    dr = ImageDraw.Draw(fake)
    for y in range(0, 96, 8):
        for x in range(0, 96, 8):
            if (x // 8 + y // 8) % 2:
                dr.rectangle([x, y, x + 7, y + 7], fill=(204, 204, 204))
    dr.ellipse([30, 30, 66, 66], fill=(160, 90, 40))
    fake.save(d / "fake_checker.png")

    mask = Image.new("L", (96, 96), 0)
    ImageDraw.Draw(mask).ellipse([20, 20, 76, 76], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    sprite = Image.new("RGBA", (96, 96), (150, 90, 40, 0))
    sprite.putalpha(mask)
    sprite.save(d / "sprite.png")

    halo = Image.new("RGBA", (96, 96), (255, 255, 255, 0))
    halo.putalpha(mask)
    core = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    inner = Image.new("L", (96, 96), 0)
    ImageDraw.Draw(inner).ellipse([26, 26, 70, 70], fill=255)
    core.paste(Image.new("RGBA", (96, 96), (150, 90, 40, 255)), (0, 0), inner)
    halo.alpha_composite(core)
    halo.save(d / "halo.png")

    edge = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    ImageDraw.Draw(edge).rectangle([0, 10, 40, 50], fill=(90, 120, 60, 255))
    edge.save(d / "touch_edge.png")

    seamless.save(d / "copy.png", optimize=True)
    changed = seamless.copy()
    ImageDraw.Draw(changed).rectangle([10, 10, 20, 20], fill=(255, 0, 0))
    changed.save(d / "changed.png")
    return {}


def test_images(d: Path) -> None:
    r = run("tile_preview.py", str(d / "seamless.png"), "--out", str(d / "out"), "--json")
    m = json.loads(r.stdout)
    check("tile: seamless image passes", r.returncode == 0 and m["seam_ratio_x"] < 1.6 and m["seam_ratio_y"] < 1.6,
          f"ratio_x={m['seam_ratio_x']} ratio_y={m['seam_ratio_y']}")
    check("tile: writes preview", Path(m["preview"]).exists())
    r = run("tile_preview.py", str(d / "seamed.png"), "--out", str(d / "out"), "--json")
    m = json.loads(r.stdout)
    check("tile: seamed image is flagged", r.returncode == 1 and m["seam_ratio_x"] > 5 and m["gradient_range"] > 24,
          f"ratio_x={m['seam_ratio_x']} gradient={m['gradient_range']}")

    r = run("alpha_check.py", str(d / "fake_checker.png"), "--out", str(d / "out"), "--json")
    m = json.loads(r.stdout)
    check("alpha: detects fake checkerboard", r.returncode == 1 and m.get("fake_checkerboard") and m["fake_checkerboard"]["block_px"] == 8,
          str(m.get("fake_checkerboard")))
    r = run("alpha_check.py", str(d / "sprite.png"), "--out", str(d / "out"), "--json")
    m = json.loads(r.stdout)
    check("alpha: normal sprite passes", r.returncode == 0 and m["semi_ratio"] > 0 and Path(m["composite"]).exists(), str(m["issues"]))
    r = run("alpha_check.py", str(d / "halo.png"), "--out", str(d / "out"), "--json")
    m = json.loads(r.stdout)
    check("alpha: detects white halo", r.returncode == 1 and any("white halo" in i for i in m["issues"]), str(m["issues"]))
    r = run("alpha_check.py", str(d / "touch_edge.png"), "--out", str(d / "out"), "--json")
    m = json.loads(r.stdout)
    check("alpha: detects edge clipping", r.returncode == 1 and any("canvas edge" in i for i in m["issues"]), str(m["issues"]))

    r = run("compare_images.py", str(d / "seamless.png"), str(d / "copy.png"), "--json")
    m = json.loads(r.stdout)
    check("compare: re-encoded file is pixel-identical", r.returncode == 0 and m["pixel_identical"] and m["max_diff"] == 0,
          f"bytes_identical={m['bytes_identical']}")
    r = run("compare_images.py", str(d / "seamless.png"), str(d / "changed.png"), "--out", str(d / "out"), "--json")
    m = json.loads(r.stdout)
    check("compare: detects change and writes strip", r.returncode == 1 and m["changed_pixel_ratio"] > 0.02 and Path(m["strip"]).exists(),
          f"changed={m['changed_pixel_ratio']}")

    r = run("contact_sheet.py", str(d / "seamless.png"), str(d / "sprite.png"), "--anchor", str(d / "copy.png"),
            "--out", str(d / "out" / "sheet.png"), "--title", "test", "--json")
    m = json.loads(r.stdout) if r.returncode == 0 else {}
    check("contact sheet: anchor and numbering", r.returncode == 0 and [i["tag"] for i in m["items"]] == ["ANCHOR", "#1", "#2"], r.stderr[-200:])


def test_artjob(d: Path) -> None:
    root = d / "proj"
    (root / "art").mkdir(parents=True)
    img = root / "art" / "concept_v1.png"
    img.write_bytes((d / "sprite.png").read_bytes())
    J = lambda *a: run("artjob.py", "--root", str(root), *a)

    r = J("init", "house_a", "--kind", "3d", "--title", "House A")
    check("job: init", r.returncode == 0 and (root / ".art-workflow" / ".gdignore").exists()
          and (root / ".art-workflow/jobs/house_a/brief.json").exists(), r.stderr)
    check("job: duplicate init rejected", J("init", "house_a", "--kind", "3d").returncode != 0)
    r = J("artifact", "house_a", "art/concept_v1.png", "--role", "concept")
    check("job: register artifact", r.returncode == 0, r.stderr)
    r = J("review", "house_a", "G2", "--artifact", "concept_v1", "--decision", "approved", "--by", "delegated_agent", "--evidence", "x")
    check("job: delegated review without authorization rejected", r.returncode != 0)
    r = J("review", "house_a", "G2", "--artifact", "concept_v1", "--decision", "approved", "--by", "user", "--evidence", "this one")
    check("job: user review recorded", r.returncode == 0, r.stderr)
    r = J("stage", "house_a", "accepted")
    check("job: cannot accept without G3", r.returncode != 0)
    r = J("stage", "house_a", "needs_reconcile")
    check("job: side state requires a note", r.returncode != 0)
    r = J("event", "house_a", "remote_task", "--data", '{"api_key":"sk-123"}')
    check("job: refuses to write credentials", r.returncode != 0)
    r = J("event", "house_a", "remote_task", "--data", '{"task_id":"t-1"}')
    check("job: records remote task", r.returncode == 0)
    r = J("spend", "house_a", "--estimated", "40", "--unit", "credits", "--channel", "web")
    check("job: records spend", r.returncode == 0)
    check("job: verify passes", J("verify", "house_a").returncode == 0)
    r = J("stage", "house_a", "asset_review_pending")
    check("job: review stage prints gate stop", r.returncode == 0 and "GATE:" in r.stdout and "end the turn" in r.stdout, r.stdout)
    check("job: open gate does not fail verify", J("verify", "house_a").returncode == 0)

    img.write_bytes((d / "seamless.png").read_bytes())
    r = J("verify", "house_a")
    check("job: verify fails after file change", r.returncode == 1 and "stale" in r.stdout, r.stdout)
    r = J("artifact", "house_a", "art/concept_v1.png", "--role", "concept")
    check("job: same name with different content rejected", r.returncode != 0)
    r = J("resume", "house_a", "--json")
    rep = json.loads(r.stdout)
    check("job: resume reports stale approval", rep["gates"]["G2"] != "approved" and rep["warnings"] and rep["spend_totals"]["credits"]["estimated"] == 40
          and rep["remote"][0]["task_id"] == "t-1", json.dumps(rep["gates"]))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("Pillow is required: python -m pip install Pillow")
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "out").mkdir()
        make_images(d)
        test_images(d)
        test_artjob(d)
    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail and not ok else ""))
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
