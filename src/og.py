"""OG image + touch icon for The Groove: a record drawn in code, half out of a kraft sleeve. No label art, logos or real covers."""
import json, math, os, random, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
H = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("GROOVE_OUT", "/home/claude/groove")
T = lambda n, s: ImageFont.truetype(f"{H}/ttf/{n}.ttf", s)
W, Hh = 1200, 630
KRAFT, INK, LABEL, CREAM, VINYL = (233, 218, 190), (28, 23, 18), (226, 69, 44), (255, 244, 230), (20, 18, 16)
im = Image.new("RGB", (W, Hh), KRAFT); d = ImageDraw.Draw(im)
random.seed(9)
for _ in range(14000):
    x, y = random.randrange(W), random.randrange(Hh); v = random.randint(-14, 8)
    d.point((x, y), fill=(KRAFT[0] + v, KRAFT[1] + v, KRAFT[2] + v))
# record
cx, cy, r = 900, 315, 290
rec = Image.new("RGBA", (W, Hh), (0, 0, 0, 0)); q = ImageDraw.Draw(rec)
q.ellipse([cx - r, cy - r, cx + r, cy + r], fill=VINYL + (255,))
for rr in range(118, r - 4, 4):
    c = 44 if rr not in (190, 230) else 20
    q.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(c, c - 4, c - 8, 255), width=1)
sh = Image.new("RGBA", (W, Hh), (0, 0, 0, 0)); sq = ImageDraw.Draw(sh)
sq.pieslice([cx - r, cy - r, cx + r, cy + r], 300, 330, fill=(255, 255, 255, 16)); sq.pieslice([cx - r, cy - r, cx + r, cy + r], 120, 150, fill=(255, 255, 255, 12))
sq.ellipse([cx - 112, cy - 112, cx + 112, cy + 112], fill=(0, 0, 0, 0))
rec.alpha_composite(sh); q = ImageDraw.Draw(rec)
q.ellipse([cx - 110, cy - 110, cx + 110, cy + 110], fill=(29, 26, 23, 255))
q.ellipse([cx - 82, cy - 82, cx + 82, cy + 82], fill=LABEL + (255,))
q.text((cx, cy - 30), "THE GROOVE", font=T("gloock-latin-400-normal", 22), fill=CREAM, anchor="mm")
q.text((cx, cy + 30), "SIDE A · 33 1/3 RPM", font=T("ibm-plex-mono-latin-600-normal", 11), fill=CREAM, anchor="mm")
q.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=KRAFT + (255,))
f = T("caveat-latin-500-normal", 17)
txt = "  A1 · groove.cold.fyi · no. 9 · etched in the dead wax ·" * 2
for i, ch in enumerate(txt):
    a = math.radians(-90 + i * 3.05)
    x, y = cx + 96 * math.cos(a), cy + 96 * math.sin(a)
    g = Image.new("RGBA", (30, 30), (0, 0, 0, 0)); ImageDraw.Draw(g).text((15, 15), ch, font=f, fill=(189, 178, 162, 255), anchor="mm")
    g = g.rotate(-math.degrees(a) - 90, resample=Image.BICUBIC)
    rec.alpha_composite(g, (int(x - 15), int(y - 15)))
shadow = Image.new("RGBA", (W, Hh), (0, 0, 0, 0)); ImageDraw.Draw(shadow).ellipse([cx - r + 10, cy - r + 18, cx + r + 10, cy + r + 18], fill=(0, 0, 0, 90))
im = im.convert("RGBA"); im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14))); im.alpha_composite(rec)
# sleeve edge over the record's left side
d = ImageDraw.Draw(im)
d.rectangle([0, 0, 640, Hh], fill=KRAFT + (255,))
for _ in range(9000):
    x, y = random.randrange(0, 640), random.randrange(Hh); v = random.randint(-14, 8)
    d.point((x, y), fill=(KRAFT[0] + v, KRAFT[1] + v, KRAFT[2] + v, 255))
d.line([(640, 0), (640, Hh)], fill=(196, 178, 146), width=3)
n_src = sys.argv[1] if len(sys.argv) > 1 else ""
d.text((60, 52), "COLD.FYI / DEEP DIVES / NO. 9", font=T("ibm-plex-mono-latin-600-normal", 19), fill=(108, 95, 80))
d.text((54, 96), "The", font=T("gloock-latin-400-normal", 92), fill=INK)
d.text((50, 178), "Groove", font=T("gloock-latin-400-normal", 168), fill=LABEL)
d.text((60, 392), "How a vinyl record gets made, sold,", font=T("crimson-pro-latin-400-italic", 36), fill=INK)
d.text((60, 436), "played and collected.", font=T("crimson-pro-latin-400-italic", 36), fill=INK)
d.text((60, 540), "GROOVE.COLD.FYI" + (f"  ·  {n_src} SOURCES" if n_src else ""), font=T("ibm-plex-mono-latin-600-normal", 20), fill=INK)
im.convert("RGB").save(f"{OUT}/og.png", optimize=True)
ic = Image.new("RGB", (180, 180), VINYL); z = ImageDraw.Draw(ic)
for rr in range(40, 88, 5):
    z.ellipse([90 - rr, 90 - rr, 90 + rr, 90 + rr], outline=(46, 41, 36), width=1)
z.ellipse([52, 52, 128, 128], fill=LABEL); z.ellipse([85, 85, 95, 95], fill=VINYL)
ic.save(f"{OUT}/apple-touch-icon.png")
print("og ok")
