"""Montage leg4 snap-fit glove panels into docs/build_plan/leg4_complete.png."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
SP = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
BP = "/home/mrqbit/Downloads/dbx-r/docs/build_plan"
BG = (36, 42, 54)

def load_crop(name, pad=18):
    im = Image.open(SP + "/" + name).convert("RGB")
    a = np.asarray(im).astype(int)
    diff = np.abs(a - np.array([13, 15, 20])).sum(2)
    ys, xs = np.where(diff > 28)
    if len(xs) < 10: return im
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, im.width)
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, im.height)
    return im.crop((x0, y0, x1, y1))

def font(sz):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()

def panel(name, label, W, H):
    im = load_crop(name)
    im.thumbnail((W - 12, H - 40), Image.LANCZOS)
    cell = Image.new("RGB", (W, H), BG)
    cell.paste(im, ((W - im.width) // 2, (H - 32 - im.height) // 2 + 6))
    d = ImageDraw.Draw(cell)
    d.rectangle([0, H - 30, W, H], fill=(22, 26, 34))
    d.text((10, H - 26), label, fill=(235, 235, 240), font=font(18))
    return cell

Wc, Hc = 640, 470
rows = [
    [("_fc4_full_SIDE.png", "SIDE - full leg 4: real-sculpt toe boot + 3 finger gloves"),
     ("_fc4_full_TOP.png",  "TOP - full leg 4"),
     ("_fc4_full_3Q.png",   "3/4 - full leg 4")],
    [("_fc4_closeup_solid.png", "GRIP CLOSE-UP - 3 DISTINCT fingers (2 prong-styled + thumb)"),
     ("_fc4_closeup_ghost.png", "GHOST - each finger in its OWN snap glove"),
     ("_fc4_open.png",          "GRIP OPEN - pinch aperture 66 mm with gloves on")],
    [("_fc4_closed.png",        "GRIP CLOSED - free to 2.0 rad (bare mech stalls ~2.15)"),
     ("_fc4_section_prim.png",  "SECTION primary glove - 0.2 mm cavity, tip pad 3.5 mm"),
     ("_fc4_section_thumb.png", "SECTION thumb glove - 0.2 mm cavity + detent ring")],
    [("_fc4_compare_orig.png",  "ORIGINAL toy 4-B foot tip (aligned, movie scale)"),
     ("_fc4_compare_ours.png",  "OURS - real 4-B stone re-purposed: toe boot + prong-grafted fingers"),
     ("_fc4_closeup_solid.png", "tip close-up (solid stone)")],
]
ncol = 3
W = ncol * Wc
title_h = 64
out = Image.new("RGB", (W, title_h + len(rows) * Hc), BG)
d = ImageDraw.Draw(out)
d.text((16, 10), "PROJECT DUET - LEG 4 tip from the ORIGINAL toy: real 4-B toe boot + 3 DISTINCT snap-fit finger gloves",
       fill=(255, 255, 255), font=font(25))
d.text((16, 42), "Toe boot = REAL 4-B sculpt surface (82% untouched, cleft de-rolled 90deg to the grip plane); primary outers 32%/33% real-prong-governed. 0.2 mm snap cavities + detents, tip pads >=3.3 mm, grip free to 2.0 rad, aperture 66 mm.",
       fill=(150, 200, 160), font=font(15))
y = title_h
for r in rows:
    for c, (nm, lab) in enumerate(r):
        out.paste(panel(nm, lab, Wc, Hc), (c * Wc, y))
    y += Hc
out.save(BP + "/leg4_complete.png")
print("SAVED", BP + "/leg4_complete.png", out.size)
