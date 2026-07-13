"""Montage LEG3 panels into docs/build_plan/leg3_complete.png (leg2 montage style)."""
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
    d.text((10, H - 26), label, fill=(235, 235, 240), font=font(17))
    return cell

Wc, Hc = 640, 470
rows = [
    [("_fc3_full_SIDE.png", "SIDE - full leg 3 solid stone: shell keeps the REAL fork window"),
     ("_fc3_full_TOP.png",  "TOP - full leg 3"),
     ("_fc3_full_3Q.png",   "3/4 - full leg 3 (fork window visible mid-tibia)")],
    [("_fc3_ghost_SIDE.png", "GHOST - chassis inside (blue frame / orange hip QDD / yellow hand)"),
     ("_fc3_ghost_3Q.png",   "GHOST 3/4 - femur/tibia/roll-servo/foot-core enclosed, 0 proud pts"),
     ("_fc3_closeup_solid.png", "GRIP CLOSE-UP - 3 DISTINCT fingers (2 fork-branch grafted + thumb)")],
    [("_fc3_closeup_ghost.png", "GHOST - each finger in its OWN snap glove"),
     ("_fc3_open.png",          "GRIP OPEN - pinch aperture 65 mm with gloves on"),
     ("_fc3_closed.png",        "GRIP CLOSED - free to 2.0 rad (bare mech stalls ~2.15)")],
    [("_fc3_section_prim.png",  "SECTION primary glove - 0.2 mm cavity, tip pad med 7-8 mm"),
     ("_fc3_section_thumb.png", "SECTION thumb glove - 0.2 mm cavity + 0.25 mm detent ring"),
     ("_fc3_compare_orig.png",  "ORIGINAL toy 3-B FORKED foot (aligned, movie scale)")],
    [("_fc3_compare_ours.png",  "OURS - 3-B re-purposed: crease-registered toe boot + branch-grafted gloves"),
     ("_fc3_full_3Q.png",       "fork character: window kept on shell; cleft continues into 1.6 mm glove seam"),
     ("_fc3_closeup_solid.png", "tip close-up (solid stone)")],
]
ncol = 3
W = ncol * Wc
title_h = 64
out = Image.new("RGB", (W, title_h + len(rows) * Hc), BG)
d = ImageDraw.Draw(out)
d.text((16, 10), "PROJECT DUET - LEG 3 complete: enclosed FORKED shell + real-sculpt toe boot + 3 DISTINCT snap-fit finger gloves",
       fill=(255, 255, 255), font=font(25))
d.text((16, 42), "Joints exact (hip0/knee158/toe328). Enclosure 0 proud (femur/tibia/roll/foot-core). Glove outers 44%/37% real-fork-branch. Boot: fork crease re-registered +60deg to glove seam; collar band is functional floor (real toe slimmer than collar - flagged). 0.2mm cavities, detents, pads>=3mm, free to 2.0rad, aperture 65mm.",
       fill=(150, 200, 160), font=font(14))
y = title_h
for r in rows:
    for c, (nm, lab) in enumerate(r):
        out.paste(panel(nm, lab, Wc, Hc), (c * Wc, y))
    y += Hc
out.save(BP + "/leg3_complete.png")
print("SAVED", BP + "/leg3_complete.png", out.size)
