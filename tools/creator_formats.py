#!/usr/bin/env python3
"""
Creator-format thumbnails, modelled on the top-performing drama/doping videos of the
channels you benchmark (see references/creators/CREATORS.md).

  trp       Total Running Productionz: 2-4 white condensed caps top-left with black
            shadow, often ending in "...", plus ONE thin hand-drawn curved arrow.
            (THIS IS TERRIBLE / THIS IS A PROBLEM / HUGE CHEATING EXPOSED...)
  finalleg  The Final Leg: huge tall white caps across the top, the person's head/arms
            in FRONT of the text (depth effect, photo pixels untouched).
            (IS SHE HEALTHY? / THIS IS SERIOUS)
  jumpman   Jumpman: plain news-article look, with a white headline box top-left and a
            white caption box at the bottom, in a plain sans font.
            (What The Enhanced Games Exposed About PEDs, 2.1M views)

Photos are only cropped/resized. Faces can be pixelated on request (--hide).

Examples:
  python tools/creator_formats.py trp --photo coach.jpg --text "THIS IS TERRIBLE..." --arrow 0.42,0.10,0.55,0.30
  python tools/creator_formats.py finalleg --photo coach.jpg --text "WHO'S TO BLAME?"
  python tools/creator_formats.py jumpman --photo coach.jpg \
      --headline "Coach accused of giving athletes PEDs." --caption "Both athletes have been suspended."
"""
import argparse
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from make_thumbnail import load_cover

HERE = os.path.dirname(os.path.abspath(__file__))
ANTON = os.path.join(HERE, "fonts", "Anton-Regular.ttf")
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
if not os.path.exists(SANS):
    SANS = os.path.join(HERE, "fonts", "BarlowCondensed-Bold.ttf")
W, H = 1280, 720


def fit(font_path, text, max_w, start, min_size=30):
    size = start
    while size > min_size:
        f = ImageFont.truetype(font_path, size)
        b = f.getbbox(text)
        if b[2] - b[0] <= max_w:
            return f
        size -= 2
    return ImageFont.truetype(font_path, min_size)


def shadow_text(canvas, xy, text, font, fill=(255, 255, 255), blur=6, offset=4, stroke=0):
    """White text with a soft black shadow, the TRP look."""
    sh = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(sh).text((xy[0] + offset, xy[1] + offset), text, font=font, fill=255,
                            stroke_width=stroke + 3, stroke_fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    canvas.paste((0, 0, 0), (0, 0), sh)
    ImageDraw.Draw(canvas).text(xy, text, font=font, fill=fill, stroke_width=stroke,
                                stroke_fill=(0, 0, 0))


def curved_arrow(canvas, x0, y0, x1, y1, color=(255, 255, 255), width=7, bend=0.35):
    """Thin hand-drawn style curved arrow from (x0,y0) to (x1,y1), pixel coords."""
    d = ImageDraw.Draw(canvas)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0), (x1 - x0)
    cx, cy = mx + nx * bend, my + ny * bend
    pts = []
    for i in range(41):
        t = i / 40
        pts.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1,
                    (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1))
    # shadow then line
    for col, w, off in (((0, 0, 0), width + 4, 3), (color, width, 0)):
        d.line([(x + off, y + off) for x, y in pts], fill=col, width=w, joint="curve")
        ex, ey = pts[-1]
        px, py = pts[-6]
        ang = math.atan2(ey - py, ex - px)
        L = 34
        for s in (-0.55, 0.55):
            d.line([(ex + off, ey + off),
                    (ex - L * math.cos(ang + s) + off, ey - L * math.sin(ang + s) + off)],
                   fill=col, width=w)


def person_mask(photo, region, thresh=105, grow=5):
    """Mask of the dark foreground (hair/skin/arms) inside region, so the person can sit
    in front of the text. Uses the photo's own pixels; nothing is repainted."""
    x0, y0, x1, y1 = region
    g = photo.convert("L")
    m = g.point(lambda v: 255 if v < thresh else 0)
    box = Image.new("L", photo.size, 0)
    ImageDraw.Draw(box).rectangle(region, fill=255)
    m = Image.composite(m, Image.new("L", photo.size, 0), box)
    m = m.filter(ImageFilter.MaxFilter(grow * 2 + 1)).filter(ImageFilter.MinFilter(grow * 2 - 1))
    m = m.filter(ImageFilter.MedianFilter(9)).filter(ImageFilter.GaussianBlur(1.2))
    return m


def build(o):
    focus = tuple(float(v) for v in o.focus.split(","))
    photo = load_cover(o.photo, W, H, focus, o.hide, "pixel", o.zoom)
    canvas = photo.copy()
    d = ImageDraw.Draw(canvas)

    if o.style == "trp":
        lines = o.text.split("|")
        f = fit(ANTON, max(lines, key=len), W * o.text_width, 110)
        y = 18
        for ln in lines:
            shadow_text(canvas, (26, y), ln, f, blur=5, offset=4, stroke=2)
            y += int(f.size * 1.12)
        if o.arrow:
            x0, y0, x1, y1 = (float(v) for v in o.arrow.split(","))
            curved_arrow(canvas, x0 * W, y0 * H, x1 * W, y1 * H, color=o.arrow_color_rgb, bend=o.bend)

    elif o.style == "finalleg" and o.side:
        # side variant ("THIS IS / SERIOUS"): huge stacked caps beside the person
        lines = o.text.split("|")
        grad = Image.new("L", (W, H), 0)
        gd = ImageDraw.Draw(grad)
        for xx in range(int(W * 0.6)):
            t = 1 - xx / (W * 0.6)
            v = int(200 * t ** 1.2)
            if o.side == "right":
                xx = W - 1 - xx
            gd.line([(xx, 0), (xx, H)], fill=v)
        canvas = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), canvas, grad)
        td = ImageDraw.Draw(canvas)
        size = 400
        while size > 60:
            f = ImageFont.truetype(ANTON, size)
            lh = int(size * 1.02)
            widest = max(f.getbbox(l)[2] - f.getbbox(l)[0] for l in lines)
            if widest <= W * o.text_width and lh * len(lines) <= H * 0.92:
                break
            size -= 4
        y = (H - lh * len(lines)) / 2 - f.getbbox("H")[1] * 0.5
        for ln in lines:
            b = f.getbbox(ln)
            x = 30 - b[0] if o.side == "left" else W - 30 - (b[2] - b[0]) - b[0]
            td.text((x, y), ln, font=f, fill=(255, 255, 255))
            y += lh

    elif o.style == "finalleg":
        lines = o.text.split("|")
        f = fit(ANTON, max(lines, key=len), W - 50, 260)
        # darken top slightly like their graded photos (overlay only)
        grad = Image.new("L", (W, H), 0)
        gd = ImageDraw.Draw(grad)
        for yy in range(int(H * 0.5)):
            gd.line([(0, yy), (W, yy)], fill=int(120 * (1 - yy / (H * 0.5))))
        canvas = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), canvas, grad)
        text_layer = canvas.copy()
        td = ImageDraw.Draw(text_layer)
        y = -int(f.size * 0.06)
        for ln in lines:
            b = f.getbbox(ln)
            x = (W - (b[2] - b[0])) / 2 - b[0] if o.center else 24 - b[0]
            td.text((x, y), ln, font=f, fill=(255, 255, 255))
            y += int(f.size * 1.0)
        if o.depth:
            rx = [float(v) for v in o.depth.split(",")]
            region = (int(rx[0] * W), int(rx[1] * H), int(rx[2] * W), int(rx[3] * H))
            m = person_mask(photo, region, o.thresh)
            # person pixels (from the shaded canvas) go back on top of the text
            text_layer.paste(canvas, (0, 0), m)
        canvas = text_layer

    elif o.style == "jumpman":
        def box(text, x, y, size, max_w):
            f = fit(SANS, text, max_w, size, 18)
            b = f.getbbox(text)
            pad = int(f.size * 0.28)
            d2 = ImageDraw.Draw(canvas)
            d2.rectangle((x, y, x + b[2] - b[0] + pad * 2, y + (b[3] - b[1]) + pad * 2),
                         fill=(255, 255, 255), outline=(200, 200, 200))
            d2.text((x + pad - b[0], y + pad - b[1]), text, font=f, fill=(20, 20, 20))
        if o.headline:
            box(o.headline, 14, 14, 44, W * 0.62)
        if o.caption:
            f = fit(SANS, o.caption, W * 0.72, 46, 18)
            b = f.getbbox(o.caption)
            box(o.caption, int(W - (b[2] - b[0]) - 80), H - 110, 46, W * 0.72)
    return canvas


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("style", choices=["trp", "finalleg", "jumpman"])
    p.add_argument("--photo", required=True)
    p.add_argument("--focus", default="0.5,0.4")
    p.add_argument("--zoom", type=float, default=1.0)
    p.add_argument("--hide", action="append", help="pixelate a face: cx,cy,rx,ry (fractions of original)")
    p.add_argument("--text", default="", help='"|" = new line')
    p.add_argument("--text-width", type=float, default=0.6)
    p.add_argument("--arrow", help="trp: x0,y0,x1,y1 as fractions (tail to head)")
    p.add_argument("--arrow-color", default="white", choices=["white", "red"])
    p.add_argument("--bend", type=float, default=0.35)
    p.add_argument("--depth", help="finalleg: x0,y0,x1,y1 region where the person goes in front of text")
    p.add_argument("--thresh", type=int, default=105, help="finalleg depth: darkness threshold")
    p.add_argument("--center", action="store_true", help="finalleg: centre the text")
    p.add_argument("--side", choices=["left", "right"], help="finalleg: stacked text beside the person instead of across the top")
    p.add_argument("--headline", help="jumpman: top headline box")
    p.add_argument("--caption", help="jumpman: bottom caption box")
    p.add_argument("--out", default="thumbnail.png")
    o = p.parse_args()
    o.arrow_color_rgb = (255, 255, 255) if o.arrow_color == "white" else (230, 20, 20)
    img = build(o)
    img.save(o.out, optimize=True)
    root, ext = os.path.splitext(o.out)
    img.resize((320, 180), Image.LANCZOS).save(f"{root}.mobile{ext}")
    print("saved", o.out)


if __name__ == "__main__":
    main()
