#!/usr/bin/env python3
"""
Pro layered thumbnails: cut people out of their photos and build a scene.

  * Person cutouts come from a LOCAL segmentation model (tools/models/selfie_multiclass.tflite);
    nothing is uploaded anywhere. The person's own pixels are never edited.
  * Only the BACKGROUND gets treated (blur / darken / tint / desaturate) so people pop.
  * Signature look: lime outline around the main person, slanted Barlow text, hard shadow,
    lime key word, tapered lime arrow, "//" mark.
  * Text can sit BEHIND a person (depth), or in front.
  * Faces can be pixelated (hide) before cutting out, e.g. minors.

Usage:  python tools/pro_thumbnail.py spec.json
Spec (paths relative to the spec file):
{
  "out": "pro-a.png",
  "background": {"photo": "photos/x.jpg", "focus": [0.5,0.4], "zoom": 1.0,
                 "blur": 8, "darken": 0.55, "tint": [120,0,0], "tint_amount": 0.25, "desaturate": 0.4},
  "subjects": [   # drawn in order; later = in front
    {"photo": "photos/coach.jpg", "cx": 0.68, "bottom": 1.08, "height": 1.15,
     "outline": 6, "outline_color": "lime", "hide": ["cx,cy,rx,ry"], "label": "SUSPENDED",
     "dim": 0.0}
  ],
  "text": [{"text": "THIS IS|*BAD...*", "box": [0.03,0.05,0.5,0.6], "layer": "front", "align": "left"}],
  "arrow": [x0,y0,x1,y1], "bend": 0.3,
  "mark": true,
  "tag": "ALLEGED"
}
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_thumbnail import hide_faces, load_cover  # noqa: E402
from signature_formats import (INK, LIME, UI, WHITE, draw_line, fit_lines, line_width,  # noqa: E402
                               slash_mark, tapered_arrow)

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "models", "selfie_multiclass.tflite")
W, H = 1280, 720
COLORS = {"lime": LIME, "white": WHITE, "black": INK, "red": (230, 25, 25)}
_interp = None


def person_alpha(im):
    """Soft person mask (0-255) from the local model. Class 0 = background."""
    global _interp
    if _interp is None:
        from ai_edge_litert.interpreter import Interpreter
        _interp = Interpreter(model_path=MODEL)
        _interp.allocate_tensors()
    inp = _interp.get_input_details()[0]
    out = _interp.get_output_details()[0]
    x = np.asarray(im.convert("RGB").resize((256, 256), Image.BILINEAR)).astype(np.float32) / 255.0
    _interp.set_tensor(inp["index"], x[None])
    _interp.invoke()
    o = _interp.get_tensor(out["index"])[0]
    e = np.exp(o - o.max(-1, keepdims=True))
    p = e / e.sum(-1, keepdims=True)
    person = 1 - p[..., 0]
    m = Image.fromarray((person * 255).astype("uint8")).resize(im.size, Image.BICUBIC)
    # tighten edges a little
    return m.point(lambda v: 0 if v < 70 else (255 if v > 190 else int((v - 70) * 255 / 120)))


def cutout(path, hide=None):
    im = Image.open(path).convert("RGB")
    alpha = person_alpha(im)          # segment the ORIGINAL photo
    if hide:
        im = hide_faces(im, hide, "pixel")
    rgba = im.convert("RGBA")
    rgba.putalpha(alpha)
    bbox = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
    return rgba.crop(bbox)


def place(canvas, sub, s):
    h = int(s.get("height", 1.0) * H)
    w = int(sub.width * h / sub.height)
    sub = sub.resize((w, h), Image.LANCZOS)
    if s.get("flip"):
        sub = sub.transpose(Image.FLIP_LEFT_RIGHT)
    if s.get("dim"):
        rgb = ImageEnhance.Brightness(sub.convert("RGB")).enhance(1 - s["dim"])
        a = sub.split()[3]
        sub = rgb.convert("RGBA")
        sub.putalpha(a)
    x = int(s.get("cx", 0.5) * W - w / 2)
    y = int(s.get("bottom", 1.0) * H - h)
    a = sub.split()[3]
    # soft drop shadow for depth
    sh = a.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.6))
    canvas.paste(INK, (x + 14, y + 10), sh)
    ol = s.get("outline", 0)
    if ol:
        grown = a.filter(ImageFilter.MaxFilter(ol * 2 + 1))
        outer = grown.filter(ImageFilter.MaxFilter(5))
        canvas.paste(INK, (x, y), outer)
        canvas.paste(COLORS.get(s.get("outline_color", "lime"), LIME), (x, y), grown)
    canvas.paste(sub, (x, y), sub)
    if s.get("label"):
        f = ImageFont.truetype(os.path.join(HERE, "fonts", "BarlowCondensed-BlackItalic.ttf"),
                               s.get("label_size", 44))
        t = s["label"].upper()
        b = f.getbbox(t)
        tw, th = b[2] - b[0], b[3] - b[1]
        lx = int(x + w / 2 - tw / 2)
        ly = int(s.get("label_y", 0.86) * H)
        d = ImageDraw.Draw(canvas)
        col = COLORS.get(s.get("label_color", "red"))
        off = (th + 24) * 0.21
        d.polygon([(lx - 16 + off, ly), (lx + tw + 16 + off, ly), (lx + tw + 16, ly + th + 24),
                   (lx - 16, ly + th + 24)], fill=col)
        d.text((lx - b[0], ly + 12 - b[1]), t, font=f, fill=WHITE)
    return canvas


def background(bg, base):
    focus = tuple(bg.get("focus", [0.5, 0.4]))
    if bg.get("color"):
        img = Image.new("RGB", (W, H), tuple(bg["color"]))
    else:
        img = load_cover(os.path.join(base, bg["photo"]), W, H, focus, bg.get("hide"), "pixel",
                         bg.get("zoom", 1.0))
    if bg.get("desaturate"):
        img = ImageEnhance.Color(img).enhance(1 - bg["desaturate"])
    if bg.get("blur"):
        img = img.filter(ImageFilter.GaussianBlur(bg["blur"]))
    if bg.get("tint"):
        img = Image.blend(img, Image.new("RGB", (W, H), tuple(bg["tint"])), bg.get("tint_amount", 0.25))
    if bg.get("darken"):
        img = ImageEnhance.Brightness(img).enhance(1 - bg["darken"])
    if bg.get("vignette", 0.5):
        v = Image.new("L", (W, H), 0)
        ImageDraw.Draw(v).ellipse((-W * 0.25, -H * 0.35, W * 1.25, H * 1.35), fill=255)
        v = v.filter(ImageFilter.GaussianBlur(160))
        img = Image.composite(img, ImageEnhance.Brightness(img).enhance(1 - bg.get("vignette", 0.5)), v)
    return img


def draw_text(canvas, t):
    x0, y0, x1, y1 = (t["box"][0] * W, t["box"][1] * H, t["box"][2] * W, t["box"][3] * H)
    lines = t["text"].split("|")
    f = fit_lines(lines, x1 - x0, y1 - y0, start=t.get("max_size", 300))
    lh = int(f.size * t.get("line_height", 0.96))
    shadow = max(5, f.size // 18)
    total = lh * len(lines)
    va = t.get("valign", "top")
    y = y0 if va == "top" else (y1 - total if va == "bottom" else (y0 + y1 - total) / 2)
    for ln in lines:
        w = line_width(ln, f)
        al = t.get("align", "left")
        x = x0 if al == "left" else (x1 - w if al == "right" else (x0 + x1 - w) / 2)
        draw_line(canvas, x, y, ln, f, LIME, shadow)
        y += lh
    return f


def build(spec, base):
    canvas = background(spec["background"], base)
    subs = spec.get("subjects", [])
    behind = [t for t in spec.get("text", []) if t.get("layer") == "behind"]
    front = [t for t in spec.get("text", []) if t.get("layer", "front") == "front"]
    # text that should sit behind the MAIN (last) subject
    for i, s in enumerate(subs):
        if i == len(subs) - 1:
            for t in behind:
                draw_text(canvas, t)
        cut = cutout(os.path.join(base, s["photo"]), s.get("hide"))
        place(canvas, cut, s)
    for t in front:
        f = draw_text(canvas, t)
        if spec.get("mark", True) and t is front[0]:
            m = int(f.size * 0.32)
            slash_mark(canvas, int(t["box"][0] * W), int(t["box"][1] * H) - m - 8, m, LIME)
    if spec.get("arrow"):
        a = spec["arrow"]
        tapered_arrow(canvas, a[0] * W, a[1] * H, a[2] * W, a[3] * H, LIME, spec.get("bend", 0.3))
    if spec.get("tag"):
        d = ImageDraw.Draw(canvas)
        f = ImageFont.truetype(UI, 34)
        t = spec["tag"].upper()
        b = f.getbbox(t)
        x, y = W - (b[2] - b[0]) - 52, 22
        d.rectangle((x - 14, y, W - 24, y + 50), fill=LIME)
        d.text((x - b[0], y + 25 - (b[1] + b[3]) / 2), t, font=f, fill=INK)
    return canvas


def main():
    spec_path = sys.argv[1]
    base = os.path.dirname(os.path.abspath(spec_path))
    with open(spec_path) as fh:
        spec = json.load(fh)
    img = build(spec, base)
    out = os.path.join(base, spec.get("out", "pro.png"))
    img.save(out, optimize=True)
    root, ext = os.path.splitext(out)
    img.resize((320, 180), Image.LANCZOS).save(f"{root}.mobile{ext}")
    print("saved", out)


if __name__ == "__main__":
    main()
