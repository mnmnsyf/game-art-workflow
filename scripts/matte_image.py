#!/usr/bin/env python3
"""Preserve native alpha, apply a supplied mask, or matte border-connected solid BG.

No network, model weights, rembg, or generation. This is not semantic segmentation.
Always creates a new PNG plus black/white/colored QA sheet; never overwrites files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageColor, ImageDraw
from _imgutil import flatten, labeled_row, utf8_stdout


def background_mask(rgb, bg, inner, outer):
    """Only erase similar pixels connected to a border; protect enclosed regions."""
    delta = ImageChops.difference(rgb, Image.new('RGB', rgb.size, bg))
    channels = delta.split()
    distance = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    connected = distance.point([255 if n <= outer else 0 for n in range(256)])
    w, h = rgb.size
    for x in range(w):
        for y in (0, h-1):
            if connected.getpixel((x, y)) == 255:
                ImageDraw.floodfill(connected, (x, y), 128)
    for y in range(h):
        for x in (0, w-1):
            if connected.getpixel((x, y)) == 255:
                ImageDraw.floodfill(connected, (x, y), 128)
    region = connected.point([255 if n == 128 else 0 for n in range(256)])
    ramp = distance.point([round(255 * max(0, min(1, (n-inner)/(outer-inner)))) for n in range(256)])
    return Image.composite(ramp, Image.new('L', rgb.size, 255), region)


def main(argv=None):
    utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mask', type=Path, help='explicit grayscale alpha, same size as input')
    parser.add_argument('--bg', help='known solid background, e.g. #ffffff')
    parser.add_argument('--inner', type=int, default=8, help='max-channel BG difference made fully transparent')
    parser.add_argument('--outer', type=int, default=32, help='max-channel BG difference at feather boundary')
    parser.add_argument('--unmix', action='store_true', help='approximate removal of a KNOWN composited solid BG')
    args = parser.parse_args(argv)
    try:
        if not 0 <= args.inner < args.outer <= 255:
            raise ValueError('require 0 <= inner < outer <= 255')
        if args.out.suffix.lower() != '.png':
            raise ValueError('output must be PNG')
        preview = args.out.with_name(args.out.stem + '_qa.png')
        for dest in (args.out, preview):
            if dest.exists() or dest.resolve() == args.input.resolve() or (args.mask and dest.resolve() == args.mask.resolve()):
                raise ValueError('output already exists or would overwrite a source; choose a new version')
        source_hash = hashlib.sha256(args.input.read_bytes()).hexdigest()
        with Image.open(args.input) as image:
            original = image.convert('RGBA')
        rgb = original.convert('RGB')
        native = original.getchannel('A')
        has_alpha = native.getextrema()[0] < 255
        bg = ImageColor.getrgb(args.bg) if args.bg else None
        warnings = []
        if bg and len(bg) != 3:
            raise ValueError('background must be an RGB color without alpha')
        if args.unmix and (bg is None or has_alpha):
            raise ValueError('unmix requires --bg and an opaque source composited over that color')
        if args.mask:
            with Image.open(args.mask) as image:
                mask = image.convert('L')
            if mask.size != rgb.size:
                raise ValueError('mask dimensions must match the source')
            alpha = ImageChops.multiply(native, mask)
            mode = 'supplied_mask'
        elif has_alpha:
            alpha = native
            mode = 'native_alpha_preserved'
        else:
            if bg is None:
                w, h = rgb.size
                corners = [rgb.getpixel(p) for p in ((0, 0), (w-1, 0), (0, h-1), (w-1, h-1))]
                bg = corners[0]
                if any(max(abs(a-b) for a, b in zip(c, bg)) > args.inner for c in corners):
                    raise ValueError('ambiguous background: provide a verified --bg or --mask, or use GPT editing')
            alpha = background_mask(rgb, bg, args.inner, args.outer)
            mode = 'border_connected_color'
            warnings.append('Color-only matting: enclosed background holes remain opaque; low-contrast or complex scenes require a supplied mask or GPT edit.')
        result = original.copy()
        result.putalpha(alpha)
        if args.unmix:
            pixels = result.load()
            for y in range(result.height):
                for x in range(result.width):
                    r, g, b, a = pixels[x, y]
                    if 0 < a < 255:
                        fraction = a / 255
                        values = [max(0, min(255, round((c-(1-fraction)*background)/fraction))) for c, background in zip((r, g, b), bg)]
                        pixels[x, y] = (*values, a)
            warnings.append('Unmix assumes the supplied mask and solid BG match the original composite; review color shifts.')
        hist = alpha.histogram()
        if hist[0] == alpha.width * alpha.height:
            raise ValueError('matte removes the entire subject; no output written')
        args.out.parent.mkdir(parents=True, exist_ok=True)
        result.save(args.out)
        qa = labeled_row([flatten(result, c) for c in ((0, 0, 0), (255, 255, 255), (65, 110, 145))],
                         ['black', 'white', 'game-like color'])
        qa.save(preview)
        print(json.dumps({'output': str(args.out.resolve()), 'preview': str(preview.resolve()), 'mode': mode,
                          'source_sha256': source_hash, 'size': result.size, 'transparent_pixels': hist[0],
                          'semi_transparent_pixels': sum(hist[1:255]), 'warnings': warnings}))
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
