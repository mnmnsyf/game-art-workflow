"""Shared helpers for the image check scripts (requires Pillow)."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    print("Pillow is required: python -m pip install Pillow", file=sys.stderr)
    sys.exit(2)

FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
]


def utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def font(size: int = 14):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def open_image(path: str | Path) -> Image.Image:
    p = Path(path)
    if not p.is_file():
        print(f"error: file not found: {p}", file=sys.stderr)
        sys.exit(2)
    img = Image.open(p)
    img.load()
    return img


def checker(size: tuple[int, int], cell: int = 8, a=(200, 200, 200), b=(255, 255, 255)) -> Image.Image:
    w, h = size
    bg = Image.new("RGB", size, b)
    d = ImageDraw.Draw(bg)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if (x // cell + y // cell) % 2:
                d.rectangle([x, y, x + cell - 1, y + cell - 1], fill=a)
    return bg


def flatten(img: Image.Image, bg) -> Image.Image:
    """Composite onto a solid colour tuple or an RGB image of the same size."""
    rgba = img.convert("RGBA")
    base = bg.copy().convert("RGBA") if isinstance(bg, Image.Image) else Image.new("RGBA", rgba.size, (*bg, 255))
    base.alpha_composite(rgba)
    return base.convert("RGB")


def luminance(rgb) -> float:
    r, g, b = rgb[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def labeled_row(images: list[Image.Image], labels: list[str], pad: int = 8) -> Image.Image:
    f = font(14)
    label_h = 22
    w = sum(i.width for i in images) + pad * (len(images) + 1)
    h = max(i.height for i in images) + label_h + pad * 2
    out = Image.new("RGB", (w, h), (32, 32, 36))
    d = ImageDraw.Draw(out)
    x = pad
    for im, lab in zip(images, labels):
        d.text((x, pad), lab, fill=(235, 235, 235), font=f)
        out.paste(im.convert("RGB"), (x, pad + label_h))
        x += im.width + pad
    return out


def default_out(src: Path, suffix: str, out: str | None) -> Path:
    if out:
        o = Path(out)
        if o.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            o.parent.mkdir(parents=True, exist_ok=True)
            return o
        o.mkdir(parents=True, exist_ok=True)
        return o / f"{src.stem}_{suffix}.png"
    return src.with_name(f"{src.stem}_{suffix}.png")
