#!/usr/bin/env python3
"""
YOUR signature formats. Same proven structure as the benchmark creators, but your own look.

Shared signature across all three (so viewers recognise you):
  * Barlow Condensed Black Italic (slanted) for all big text, never Impact/Anton
  * a hard, sharp black offset shadow (no blurry glow)
  * ONE accent colour (lane lime), used only for the key word / pointer / marks
  * a small lime "//" mark

  situation  (structure from TRP)        short text top-left + one tapered lime arrow
  statement  (structure from Final Leg)  huge stacked text beside the person, last word lime
  report     (structure from Jumpman)    black news-caption boxes with a lime edge + "REPORTED" tag

Text: "|" = new line, *word* = lime key word.
Photos are only cropped/resized; faces pixelated only if you pass --hide.

  python tools/signature_formats.py situation --photo p.jpg --text "THIS IS *BAD...*" --arrow 0.30,0.22,0.47,0.40
  python tools/signature_formats.py statement --photo p.jpg --text "WHO'S|TO *BLAME?*" --side left
  python tools/signature_formats.py report --photo p.jpg --headline "Coach accused of ..." --caption "Two athletes suspended."
"""
import argparse
import math
import os
import re

from PIL import Image, ImageDraw, ImageFont

from make_thumbnail import load_cover

HERE = os.path.dirname(os.path.abspath(__file__))
SLANTED = os.path.join(HERE, "fonts", "BarlowCondensed-BlackItalic.ttf")
UI = os.path.join(HERE, "fonts", "BarlowCondensed-Bold.ttf")
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
if not os.path.exists(SANS):
    SANS = UI
W, H = 1280, 720
WHITE, INK = (255, 255, 255), (8, 8, 10)
LIME = (212, 255, 0)


def words_of(line):
    out = []
    for tok in re.findall(r"\*[^*]+\*|\S+", line):
        if tok.startswith("*") and tok.endswith("*"):
            out += [(w, True) for w in tok[1:-1].split()]
        else:
            out.append((tok, False))
    return out


def plain(line):
    return line.replace("*", "")


def draw_line(canvas, x, y, line, font, accent, shadow):
    d = ImageDraw.Draw(canvas)
    space = int(font.size * 0.2)
    for w, hl in words_of(line):
        b = font.getbbox(w)
        d.text((x - b[0] + shadow, y + shadow), w, font=font, fill=INK)
        d.text((x - b[0], y), w, font=font, fill=accent if hl else WHITE)
        x += (b[2] - b[0]) + space
    return x


def line_width(line, font):
    space = int(font.size * 0.2)
    ws = words_of(line)
    return sum(font.getbbox(w)[2] - font.getbbox(w)[0] for w, _ in ws) + space * (len(ws) - 1)


def fit_lines(lines, max_w, max_h, start=320, lh_ratio=0.98):
    size = start
    while size > 40:
        f = ImageFont.truetype(SLANTED, size)
        if max(line_width(l, f) for l in lines) <= max_w and int(size * lh_ratio) * len(lines) <= max_h:
            return f
        size -= 3
    return ImageFont.truetype(SLANTED, 40)


def slash_mark(canvas, x, y, size, accent):
    """Signature '//' mark."""
    d = ImageDraw.Draw(canvas)
    w = size * 0.22
    for k in range(2):
        ox = x + k * size * 0.42
        d.polygon([(ox + size * 0.35, y), (ox + size * 0.35 + w, y), (ox + w, y + size), (ox, y + size)],
                  fill=accent)


def tapered_arrow(canvas, x0, y0, x1, y1, accent, bend=0.3):
    """Lime arrow that thickens toward the head: your take on the pointer."""
    d = ImageDraw.Draw(canvas)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    cx, cy = mx - (y1 - y0) * bend, my + (x1 - x0) * bend
    pts = [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1,
            (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1) for t in [i / 60 for i in range(61)]]
    for col, extra, off in ((INK, 4, 4), (accent, 0, 0)):
        for i in range(len(pts) - 1):
            wdt = int(4 + 10 * (i / len(pts)) + extra)
            d.line([(pts[i][0] + off, pts[i][1] + off), (pts[i + 1][0] + off, pts[i + 1][1] + off)],
                   fill=col, width=wdt)
        ex, ey = pts[-1]
        px, py = pts[-8]
        a = math.atan2(ey - py, ex - px)
        L, spread = 46 + extra, 0.5
        tip = (ex + 14 * math.cos(a) + off, ey + 14 * math.sin(a) + off)
        d.polygon([tip,
                   (ex - L * math.cos(a - spread) + off, ey - L * math.sin(a - spread) + off),
                   (ex - L * math.cos(a + spread) + off, ey - L * math.sin(a + spread) + off)], fill=col)


def side_shade(canvas, side, strength=0.8, reach=0.6):
    grad = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(grad)
    for i in range(int(W * reach)):
        t = 1 - i / (W * reach)
        x = i if side == "left" else W - 1 - i
        gd.line([(x, 0), (x, H)], fill=int(255 * strength * t ** 1.3))
    return Image.composite(Image.new("RGB", (W, H), INK), canvas, grad)


def top_shade(canvas, strength=0.6, reach=0.4):
    grad = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(grad)
    for y in range(int(H * reach)):
        gd.line([(0, y), (W, y)], fill=int(255 * strength * (1 - y / (H * reach)) ** 1.3))
    return Image.composite(Image.new("RGB", (W, H), INK), canvas, grad)


def build(o):
    focus = tuple(float(v) for v in o.focus.split(","))
    canvas = load_cover(o.photo, W, H, focus, o.hide, "pixel", o.zoom)

    if o.style == "situation":
        canvas = top_shade(canvas, 0.55, 0.35)
        lines = o.text.split("|")
        f = fit_lines(lines, W * o.text_width, H * 0.30, start=130)
        shadow = max(4, f.size // 22)
        slash_mark(canvas, 30, 30, int(f.size * 0.62), LIME)
        x0 = 30 + int(f.size * 0.62 * 0.8) + 18
        y = 18
        for ln in lines:
            draw_line(canvas, x0, y, ln, f, LIME, shadow)
            y += int(f.size * 0.98)
        if o.arrow:
            a = [float(v) for v in o.arrow.split(",")]
            tapered_arrow(canvas, a[0] * W, a[1] * H, a[2] * W, a[3] * H, LIME, o.bend)

    elif o.style == "statement":
        canvas = side_shade(canvas, o.side, 0.85, 0.6)
        lines = o.text.split("|")
        f = fit_lines(lines, W * o.text_width, H * 0.80)
        lh = int(f.size * 0.98)
        shadow = max(5, f.size // 20)
        total = lh * len(lines)
        y = (H - total) / 2 + 20
        mark = int(f.size * 0.28)
        mx = 36 if o.side == "left" else W - 36 - mark
        slash_mark(canvas, mx, y - mark - 10, mark, LIME)
        for i, ln in enumerate(lines):
            if i == len(lines) - 1 and "*" not in o.text:
                ln = "*" + ln + "*"
            w = line_width(ln, f)
            x = 30 if o.side == "left" else W - 30 - w
            draw_line(canvas, x, y, ln, f, LIME, shadow)
            y += lh

    elif o.style == "report":
        d = ImageDraw.Draw(canvas)

        def box(text, x, y, size, max_w, right=False):
            size_ = size
            while size_ > 18:
                f = ImageFont.truetype(SANS, size_)
                b = f.getbbox(text)
                if b[2] - b[0] <= max_w:
                    break
                size_ -= 2
            b = f.getbbox(text)
            pad = int(f.size * 0.38)
            bw, bh = (b[2] - b[0]) + pad * 2 + 12, (b[3] - b[1]) + pad * 2
            if right:
                x = W - bw - x
            d.rectangle((x + 5, y + 5, x + bw + 5, y + bh + 5), fill=(0, 0, 0))
            d.rectangle((x, y, x + bw, y + bh), fill=INK)
            d.rectangle((x, y, x + 12, y + bh), fill=LIME)
            d.text((x + 12 + pad - b[0], y + pad - b[1]), text, font=f, fill=WHITE)
            return x, y, bw, bh

        if o.headline:
            hx, hy, hw, hh = box(o.headline, 24, 70, 46, W * 0.66)
            # "REPORTED" tag above the headline
            tf = ImageFont.truetype(UI, 30)
            tb = tf.getbbox(o.tag.upper())
            d.rectangle((hx, hy - 44, hx + (tb[2] - tb[0]) + 30, hy - 4), fill=LIME)
            d.text((hx + 15 - tb[0], hy - 24 - (tb[1] + tb[3]) / 2), o.tag.upper(), font=tf, fill=INK)
        if o.caption:
            box(o.caption, 30, H - 120, 46, W * 0.7, right=True)
    return canvas


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("style", choices=["situation", "statement", "report"])
    p.add_argument("--photo", required=True)
    p.add_argument("--focus", default="0.5,0.4")
    p.add_argument("--zoom", type=float, default=1.0)
    p.add_argument("--hide", action="append", help="pixelate a face: cx,cy,rx,ry (fractions of original)")
    p.add_argument("--text", default="")
    p.add_argument("--text-width", type=float, default=0.5)
    p.add_argument("--arrow", help="situation: x0,y0,x1,y1 fractions, tail to head")
    p.add_argument("--bend", type=float, default=0.3)
    p.add_argument("--side", default="left", choices=["left", "right"])
    p.add_argument("--headline")
    p.add_argument("--caption")
    p.add_argument("--tag", default="REPORTED")
    p.add_argument("--out", default="thumbnail.png")
    o = p.parse_args()
    img = build(o)
    img.save(o.out, optimize=True)
    root, ext = os.path.splitext(o.out)
    img.resize((320, 180), Image.LANCZOS).save(f"{root}.mobile{ext}")
    print("saved", o.out)


if __name__ == "__main__":
    main()
