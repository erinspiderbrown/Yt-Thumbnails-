#!/usr/bin/env python3
"""
Photo Finish: house-style thumbnail maker for a track & field channel.

Your photos are NEVER retouched, filtered, face-edited or AI-altered.
The only thing done to a photo is crop + resize to 1280x720.
Everything else (text, markers, timing chip, shade) is layered ON TOP.

Quick examples
--------------
  # Opinion / take: headline on top, one word highlighted
  python tools/make_thumbnail.py --photo me.jpg --text "TOO GOOD|TO BE *TRUE?*" --out out.png

  # Point at someone with the photo-finish line (instead of a cartoon arrow)
  python tools/make_thumbnail.py --photo race.jpg --text "NOBODY|SAW *THIS*" --finish-line 0.62

  # Analysis: timing-board chip
  python tools/make_thumbnail.py --photo race.jpg --text "*HOW?*" --clock "9.89" --clock-label "100M · AGE 17"

  # Rivalry / you vs them: two photos split by a slanted lane line
  python tools/make_thumbnail.py --photo a.jpg --photo2 b.jpg --layout split --text "WHO *WINS?*"

  # Story with 3 people; hide minors' faces (fractions of the ORIGINAL photo)
  python tools/make_thumbnail.py --layout trio --photo coach.jpg --photo2 a.jpg --photo3 b.jpg \
      --hide2 0.49,0.29,0.12,0.11 --label2 SUSPENDED --label3 SUSPENDED --text "*ALLEGEDLY*"

  # Or keep the settings in a JSON file (keys = option names with underscores)
  python tools/make_thumbnail.py --spec videos/002-foo/thumb.json

Text syntax: "|" starts a new line, *word* gets the highlight-bar treatment.
"""
import argparse
import json
import math
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_HEAD = os.path.join(HERE, "fonts", "BarlowCondensed-BlackItalic.ttf")
FONT_UI = os.path.join(HERE, "fonts", "BarlowCondensed-Bold.ttf")

W, H = 1280, 720
SLANT = 0.21          # horizontal shift per pixel of height for slanted shapes (~12°)

# House palette (override accent with --accent)
INK = (10, 10, 12)
WHITE = (255, 255, 255)
ACCENTS = {
    "lime": (212, 255, 0),     # default: lane-marker lime, pops on red track AND blue track
    "orange": (255, 106, 0),
    "cyan": (0, 224, 255),
    "gold": (255, 196, 0),
}


# ---------------------------------------------------------------- photo
def hide_faces(im, regions, mode="pixel"):
    """PRIVACY ONLY: pixelate (or blur) ellipses you list, e.g. minors' faces.
    regions = ["cx,cy,rx,ry", ...] as fractions of the ORIGINAL photo."""
    from PIL import ImageFilter
    sw, sh = im.size
    for reg in regions or []:
        cx, cy, rx, ry = (float(v) for v in reg.split(","))
        box = (int((cx - rx) * sw), int((cy - ry) * sh), int((cx + rx) * sw), int((cy + ry) * sh))
        patch = im.crop(box)
        if mode == "blur":
            patch = patch.filter(ImageFilter.GaussianBlur(max(patch.size) / 6))
        else:
            block = max(6, max(patch.size) // 9)
            small = patch.resize((max(1, patch.width // block), max(1, patch.height // block)), Image.BILINEAR)
            patch = small.resize(patch.size, Image.NEAREST)
        mask = Image.new("L", patch.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, patch.width - 1, patch.height - 1), fill=255)
        im.paste(patch, box[:2], mask)
    return im


def load_cover(path, box_w, box_h, focus=(0.5, 0.4), hide=None, hide_mode="pixel"):
    """Crop-to-fill. No colour, face or pixel edits, only crop + resize
    (plus face hiding ONLY where you explicitly ask for it with --hide*)."""
    im = Image.open(path).convert("RGB")
    if hide:
        im = hide_faces(im, hide, hide_mode)
    sw, sh = im.size
    scale = max(box_w / sw, box_h / sh)
    nw, nh = math.ceil(sw * scale), math.ceil(sh * scale)
    im = im.resize((nw, nh), Image.LANCZOS)
    fx, fy = focus
    left = int(min(max(fx * nw - box_w / 2, 0), nw - box_w))
    top = int(min(max(fy * nh - box_h / 2, 0), nh - box_h))
    return im.crop((left, top, left + box_w, top + box_h))


def shade(canvas, where, strength):
    """Soft dark gradient behind text only, so the photo itself is untouched."""
    if strength <= 0:
        return canvas
    grad = Image.new("L", (W, H), 0)
    px = grad.load()
    for y in range(H):
        for x in range(0, W, 4):
            if where == "top":
                t = max(0.0, 1 - y / (H * 0.55))
            elif where == "bottom":
                t = max(0.0, (y - H * 0.45) / (H * 0.55))
            elif where == "left":
                t = max(0.0, 1 - x / (W * 0.62))
            else:
                t = 0
            v = int(255 * strength * (t ** 1.4))
            for k in range(4):
                if x + k < W:
                    px[x + k, y] = v
    black = Image.new("RGB", (W, H), INK)
    return Image.composite(black, canvas, grad)


# ---------------------------------------------------------------- shapes
def parallelogram(draw, x0, y0, x1, y1, fill, slant=SLANT):
    h = y1 - y0
    off = h * slant
    draw.polygon([(x0 + off, y0), (x1 + off, y0), (x1, y1), (x0, y1)], fill=fill)


def parse_text(text):
    """'TOO GOOD|TO BE *TRUE?*' -> [[('TOO',False),('GOOD',False)], [...]]"""
    lines = []
    for raw in text.split("|"):
        words = []
        for tok in re.findall(r"\*[^*]+\*|\S+", raw.strip()):
            if tok.startswith("*") and tok.endswith("*"):
                for w in tok[1:-1].split():
                    words.append((w, True))
            else:
                words.append((tok, False))
        lines.append(words)
    return lines


def measure_line(font, words, space):
    widths = [font.getbbox(w)[2] - font.getbbox(w)[0] for w, _ in words]
    return widths, sum(widths) + space * (len(words) - 1)


def fit_font(lines, max_w, max_h, start=230, min_size=60):
    size = start
    while size > min_size:
        f = ImageFont.truetype(FONT_HEAD, size)
        space = int(size * 0.18)
        lh = int(size * 0.92)
        widest = max(measure_line(f, l, space)[1] + size * 0.35 for l in lines)
        if widest <= max_w and lh * len(lines) <= max_h:
            return f, size
        size -= 4
    return ImageFont.truetype(FONT_HEAD, min_size), min_size


def draw_headline(canvas, lines, area, accent, align="left"):
    """Slanted heavy italic caps, hard offset shadow, highlighted words on a lime bar."""
    x0, y0, x1, y1 = area
    font, size = fit_font(lines, x1 - x0, y1 - y0)
    space = int(size * 0.18)
    lh = int(size * 0.92)
    shadow = max(4, size // 28)
    d = ImageDraw.Draw(canvas)
    total_h = lh * len(lines)
    y = y1 - total_h if align in ("bottom", "center_bottom") else y0
    for words in lines:
        widths, line_w = measure_line(font, words, space)
        x = x0 if align in ("left", "bottom") else x0 + ((x1 - x0) - line_w) / 2
        asc = font.getbbox("H")
        cap_top, cap_bot = asc[1], asc[3]
        for (w, hl), ww in zip(words, widths):
            bx = font.getbbox(w)
            if hl:
                pad_x, pad_y = size * 0.10, size * 0.07
                parallelogram(d, x - pad_x, y + cap_top - pad_y, x + ww + pad_x,
                              y + cap_bot + pad_y, fill=accent)
                d.text((x - bx[0], y), w, font=font, fill=INK)
            else:
                d.text((x - bx[0] + shadow, y + shadow), w, font=font, fill=INK)
                d.text((x - bx[0], y), w, font=font, fill=WHITE)
            x += ww + space
        y += lh
    return canvas


def draw_finish_line(canvas, x_frac, accent):
    """Photo-finish camera line: a thin vertical line with timing ticks. Points at the subject."""
    d = ImageDraw.Draw(canvas)
    x = int(W * x_frac)
    d.rectangle((x - 3, 0, x + 3, H), fill=accent)
    for i, y in enumerate(range(18, H, 36)):
        ln = 22 if i % 5 == 0 else 11
        d.rectangle((x + 6, y, x + 6 + ln, y + 3), fill=accent)
    d.polygon([(x - 18, 0), (x + 18, 0), (x, 24)], fill=accent)
    return canvas


def draw_ring(canvas, cx, cy, r, accent):
    """Lane-marker ring around something in the photo."""
    d = ImageDraw.Draw(canvas)
    x, y, rr = int(cx * W), int(cy * H), int(r * H)
    for k in range(7):
        d.ellipse((x - rr - k, y - rr - k, x + rr + k, y + rr + k), outline=accent)
    return canvas


def draw_clock(canvas, value, label, accent, pos="tr"):
    """Stadium timing-board chip."""
    d = ImageDraw.Draw(canvas)
    f_big = ImageFont.truetype(FONT_HEAD, 150)
    f_lab = ImageFont.truetype(FONT_UI, 34)
    vb = f_big.getbbox(value)
    vw, vh = vb[2] - vb[0], vb[3] - vb[1]
    lw = (f_lab.getbbox(label)[2] if label else 0)
    bw = max(vw, lw) + 90
    bh = vh + (70 if label else 40) + 20
    x0 = W - bw - 40 if "r" in pos else 40
    y0 = 36 if "t" in pos else H - bh - 36
    parallelogram(d, x0, y0, x0 + bw, y0 + bh, fill=INK)
    parallelogram(d, x0, y0 + bh - 10, x0 + bw, y0 + bh, fill=accent)
    tx = x0 + 45 + (bh * SLANT) * 0.5
    if label:
        d.text((tx, y0 + 14), label.upper(), font=f_lab, fill=WHITE)
        d.text((tx - vb[0], y0 + 52 - vb[1]), value, font=f_big, fill=accent)
    else:
        d.text((tx - vb[0], y0 + 20 - vb[1]), value, font=f_big, fill=accent)
    return canvas


def draw_tag(canvas, tag, accent):
    """Small brand tab, bottom-left. Same spot every video = recognisable."""
    d = ImageDraw.Draw(canvas)
    f = ImageFont.truetype(FONT_HEAD, 40)
    b = f.getbbox(tag.upper())
    tw = b[2] - b[0]
    x0, y1 = 0, H - 28
    y0 = y1 - 54
    parallelogram(d, x0 - 20, y0, x0 + tw + 56, y1, fill=accent)
    d.text((x0 + 22 - b[0], y0 + 6 - b[1] + 4), tag.upper(), font=f, fill=INK)
    return canvas


def draw_panel_label(canvas, text, right_x, y, accent):
    """Right-aligned stamp on a panel, e.g. 'SUSPENDED'."""
    if not text:
        return canvas
    d = ImageDraw.Draw(canvas)
    f = ImageFont.truetype(FONT_HEAD, 46)
    b = f.getbbox(text.upper())
    tw = b[2] - b[0]
    x = right_x - tw - 30
    parallelogram(d, x - 14, y, x + tw + 24, y + 58, fill=accent)
    d.text((x - b[0], y + 6 - b[1] + 2), text.upper(), font=f, fill=INK)
    return canvas


def draw_names(canvas, left, right, accent):
    d = ImageDraw.Draw(canvas)
    f = ImageFont.truetype(FONT_HEAD, 46)
    for text, side in ((left, "l"), (right, "r")):
        if not text:
            continue
        b = f.getbbox(text.upper())
        tw = b[2] - b[0]
        x = 40 if side == "l" else W - tw - 80
        y = 36
        parallelogram(d, x - 14, y, x + tw + 24, y + 58, fill=INK)
        d.text((x - b[0], y + 6 - b[1] + 2), text.upper(), font=f, fill=WHITE)
    return canvas


# ---------------------------------------------------------------- compose
def build(o):
    accent = ACCENTS.get(o.accent, None)
    if accent is None:
        hx = o.accent.lstrip("#")
        accent = tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))
    focus = tuple(float(v) for v in o.focus.split(","))

    if o.layout == "trio":
        if not (o.photo2 and o.photo3):
            sys.exit("--layout trio needs --photo2 and --photo3")
        focus2 = tuple(float(v) for v in o.focus2.split(","))
        focus3 = tuple(float(v) for v in o.focus3.split(","))
        lw = int(W * 0.56)
        off = H * SLANT / 2
        main = load_cover(o.photo, lw + int(off) + 40, H, focus, o.hide, o.hide_mode)
        rw = W - lw + int(off) + 40
        top = load_cover(o.photo2, rw, H // 2, focus2, o.hide2, o.hide_mode)
        bot = load_cover(o.photo3, rw, H // 2, focus3, o.hide3, o.hide_mode)
        canvas = Image.new("RGB", (W, H), INK)
        canvas.paste(top, (W - rw, 0))
        canvas.paste(bot, (W - rw, H // 2))
        mask = Image.new("L", main.size, 0)
        ImageDraw.Draw(mask).polygon([(0, 0), (lw + off, 0), (lw - off, H), (0, H)], fill=255)
        canvas.paste(main, (0, 0), mask)
        d = ImageDraw.Draw(canvas)
        d.rectangle((lw - off, H // 2 - 5, W, H // 2 + 5), fill=accent)
        d.line([(lw + off, 0), (lw - off, H)], fill=accent, width=12)
        text_where = "bottom"
    elif o.layout == "split":
        if not o.photo2:
            sys.exit("--layout split needs --photo2")
        focus2 = tuple(float(v) for v in o.focus2.split(","))
        a_half = load_cover(o.photo, W // 2 + 120, H, focus, o.hide, o.hide_mode)
        b_half = load_cover(o.photo2, W // 2 + 120, H, focus2, o.hide2, o.hide_mode)
        canvas = Image.new("RGB", (W, H), INK)
        canvas.paste(a_half, (0, 0))
        # slanted divider: right photo overlaps on a diagonal
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        mid = W // 2
        off = H * SLANT / 2
        md.polygon([(mid + off, 0), (W, 0), (W, H), (mid - off, H)], fill=255)
        canvas.paste(b_half, (W - b_half.width, 0), mask.crop((W - b_half.width, 0, W, H)))
        d = ImageDraw.Draw(canvas)
        d.line([(mid + off, 0), (mid - off, H)], fill=accent, width=14)
        text_where = "bottom"
    else:
        canvas = load_cover(o.photo, W, H, focus, o.hide, o.hide_mode)
        text_where = o.layout  # top | bottom | left

    canvas = shade(canvas, text_where if o.text else "none", o.shade)

    if o.finish_line is not None:
        draw_finish_line(canvas, o.finish_line, accent)
    if o.ring:
        cx, cy, r = (float(v) for v in o.ring.split(","))
        draw_ring(canvas, cx, cy, r, accent)
    if o.layout == "split" and (o.name1 or o.name2):
        draw_names(canvas, o.name1, o.name2, accent)
    if o.layout == "trio":
        draw_panel_label(canvas, o.label2, W - 30, 22, accent)
        draw_panel_label(canvas, o.label3, W - 30, H // 2 + 22, accent)

    if o.text:
        lines = parse_text(o.text)
        if text_where == "top":
            area, align = (44, 26, W * o.text_width, H * 0.52), "left"
        elif text_where == "bottom":
            area, align = (44, H * 0.50, W * o.text_width, H - 34), "bottom"
            if o.layout == "trio":
                area, align = (40, H * 0.48, W * 0.50, H - 112), "bottom"
            if o.layout == "split":
                area, align = (60, H * 0.70, W - 60, H - 30), "center"
        else:  # left
            area, align = (44, 40, W * min(o.text_width, 0.58), H - 110), "left"
        if align == "center":
            # centre block vertically at the bottom
            draw_headline(canvas, lines, area, accent, align="center_bottom")
        else:
            draw_headline(canvas, lines, area, accent, align=align)

    if o.clock:
        draw_clock(canvas, o.clock, o.clock_label, accent, o.clock_pos)
    if o.tag:
        draw_tag(canvas, o.tag, accent)
    return canvas


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--spec", help="JSON file with any of the options below")
    p.add_argument("--photo")
    p.add_argument("--photo2", help="second photo for --layout split")
    p.add_argument("--focus", default="0.5,0.4", help="crop centre as x,y fractions (0-1)")
    p.add_argument("--focus2", default="0.5,0.4")
    p.add_argument("--photo3", help="third photo for --layout trio (bottom-right panel)")
    p.add_argument("--focus3", default="0.5,0.4")
    p.add_argument("--hide", action="append", help="PRIVACY: hide a face in photo 1, cx,cy,rx,ry fractions (repeatable)")
    p.add_argument("--hide2", action="append", help="hide a face in photo 2")
    p.add_argument("--hide3", action="append", help="hide a face in photo 3")
    p.add_argument("--hide-mode", default="pixel", choices=["pixel", "blur"])
    p.add_argument("--label2", help="trio: stamp on top-right panel, e.g. SUSPENDED")
    p.add_argument("--label3", help="trio: stamp on bottom-right panel")
    p.add_argument("--layout", default="top", choices=["top", "bottom", "left", "split", "trio"])
    p.add_argument("--text", default="", help='"LINE ONE|LINE *TWO*", | = new line, *x* = highlight')
    p.add_argument("--text-width", type=float, default=0.80, help="fraction of width text may use")
    p.add_argument("--accent", default="lime", help="lime|orange|cyan|gold or hex like #D4FF00")
    p.add_argument("--shade", type=float, default=0.75, help="0 = no darkening behind text")
    p.add_argument("--finish-line", type=float, help="x position (0-1) of photo-finish marker")
    p.add_argument("--ring", help="cx,cy,r as fractions, ring around a subject")
    p.add_argument("--clock", help='timing chip value, e.g. "9.89"')
    p.add_argument("--clock-label", default="", help='small label above the time, e.g. "100M · AGE 17"')
    p.add_argument("--clock-pos", default="tr", choices=["tr", "tl", "br", "bl"])
    p.add_argument("--name1", help="split layout: left name tag")
    p.add_argument("--name2", help="split layout: right name tag")
    p.add_argument("--tag", help="small brand tab bottom-left, e.g. 'MY TAKE' or your channel name")
    p.add_argument("--out", default="thumbnail.png")
    o = p.parse_args(argv)

    if o.spec:
        with open(o.spec) as fh:
            spec = json.load(fh)
        base = os.path.dirname(os.path.abspath(o.spec))
        for k, v in spec.items():
            if k in ("photo", "photo2", "out") and v and not os.path.isabs(v):
                v = os.path.normpath(os.path.join(base, v))
            setattr(o, k.replace("-", "_"), v)
    if not o.photo:
        p.error("--photo is required")

    img = build(o)
    os.makedirs(os.path.dirname(os.path.abspath(o.out)), exist_ok=True)
    img.save(o.out, optimize=True)
    # phone-size preview so you can check it reads small
    small = img.resize((320, 180), Image.LANCZOS)
    root, ext = os.path.splitext(o.out)
    small.save(f"{root}.mobile{ext}")
    print(f"saved {o.out}  (+ {root}.mobile{ext} at phone size)")


if __name__ == "__main__":
    main()
