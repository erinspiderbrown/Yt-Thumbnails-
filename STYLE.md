# Thumbnail styles

**For drama / controversy / doping videos, use `tools/creator_formats.py`** (TRP, Final Leg
and Jumpman formats). Your benchmark creators' best drama thumbnails are plain photos +
plain white text. See `videos/002-coach-ped-suspensions/`.

The "Photo Finish" house style below is for analysis, record and rivalry videos.

# House Style: "Photo Finish"

Your own look, built on track itself. It takes the *lessons* from the creators you
follow (short hook text, one clear subject, consistent branding) without copying
anyone's look.

## Promise: your photos are never altered
The thumbnail maker only **crops and resizes** your photo. No face edits, no
skin smoothing, no AI, no filters, no colour changes. Everything else sits on
top: text, markers, and an optional dark gradient behind the text (`--shade 0`
turns it off).

## Signature elements

| Element | What it is | Why it's yours |
|---|---|---|
| **Slanted heavy italic caps** | Barlow Condensed Black Italic, white, hard black offset shadow | Speed slant. The Final Leg uses upright tall caps and TRP uses plain white, so this reads differently at a glance. No blurry glow, so it doesn't look AI-made |
| **Lane-lime highlight bar** | The key word in black on a slanted lime bar | One colour, every video. Lime pops on both red and blue tracks |
| **Photo-finish line** | Vertical lime line with timing ticks | Replaces the cartoon red arrow everyone uses. It points at the subject in a track way |
| **Lane ring** | Lime circle around a detail (spikes, bib, clock) | For "look at this" moments |
| **Timing board chip** | Black slanted box, lime digits, small label | For times, records and splits. Instantly says "track" |
| **Brand tab** | Small lime tab bottom-left ("MY TAKE" or your name) | Same spot every video, so viewers learn it |
| **Lane-line split** | Two photos split by a slanted lime line, name tags | Rivalries, you vs them, then vs now |

## Which layout for which video
| Video type | Layout | Example |
|---|---|---|
| Opinion / hot take | `--layout left` + `--tag "MY TAKE"` | `tools/examples/take.png` |
| Controversy / "look at this" | `--layout top` + `--finish-line` or `--ring` | `tools/examples/finish-line.png` |
| Records / analysis | `--layout bottom` + `--clock` | `tools/examples/clock.png` |
| Rivalry / comparison | `--layout split` + `--name1/--name2` | `tools/examples/split.png` |

## Privacy: hiding faces (opt-in only)
For stories about minors, accused people or anyone who shouldn't be identifiable,
pixelate a face with `--hide cx,cy,rx,ry` (`--hide2`/`--hide3` for the other photos,
fractions of the ORIGINAL photo). `--hide-mode blur` gives a soft blur instead of
pixels. Nothing is hidden unless you ask. The `trio` layout (one main photo + two
stacked panels with `--label2/--label3` stamps) is made for these stories. See
`videos/002-coach-ped-suspensions/`.

## The #1 rule: one big face
The main face should fill **40–60% of the frame height** (use `--zoom`). Text goes
on the empty side, where the person is looking. Extra people become small
`--cards` (evidence prints with a red stamp), never equal panels. Multi-panel
collages read like a news page, not a moment.

## Text rules
- 2–4 words, as BIG as possible. One highlighted word, the one that carries the emotion.
- Thumbnail text should add to the title, not repeat it.
- Questions work great for takes: "TOO GOOD TO BE *TRUE?*", "*OVERRATED?*"

## Photo tips (this matters more than anything)
- **Use real photos**: your own face on camera, or race photos you have the rights to.
  Your face reacting (skeptical, shocked, laughing) like Trenton's beats a fake shocked face.
- A face that fills at least 1/3 of the height reads at phone size.
- Shoot your reaction photos against a plain background with window light.
- Check the auto-generated `.mobile.png`. If you can't read it at that size, cut words.

## Make one
```bash
pip install -r tools/requirements.txt
python tools/make_thumbnail.py --photo my-photo.jpg --layout left \
  --text "TOO GOOD|TO BE *TRUE?*" --tag "MY TAKE" --out videos/002-x/thumb.png
```
Every option is listed in `python tools/make_thumbnail.py --help`. `--focus x,y`
moves the crop (0–1). `--accent` changes the colour if you ever rebrand.
