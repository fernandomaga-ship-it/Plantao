#!/usr/bin/env python3
"""
Gera card 1080x1080 para Instagram usando Pillow.
Uso: python3 make_card.py <topic_id> <output_path>
"""
import sys, json, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).parent

FONT_PATHS_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]
FONT_PATHS_REG = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
] + FONT_PATHS_BOLD

def load_font(size, bold=True):
    for p in (FONT_PATHS_BOLD if bold else FONT_PATHS_REG):
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

PALETTES = {
    "#0C447C": {"bg": (12, 68, 124),  "bg2": (8, 45, 85)},
    "#185FA5": {"bg": (24, 95, 165),  "bg2": (14, 65, 115)},
    "#3B6D11": {"bg": (59, 109, 17),  "bg2": (35, 75, 8)},
    "#BA7517": {"bg": (186, 117, 23), "bg2": (130, 80, 12)},
    "#993C1D": {"bg": (153, 60, 29),  "bg2": (110, 40, 18)},
}

def lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def draw_gradient(img, c1, c2):
    draw = ImageDraw.Draw(img)
    for y in range(img.height):
        draw.line([(0, y), (img.width, y)], fill=lerp(c1, c2, y / img.height))

def rounded_rect(draw, xy, r, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0+r, y0, x1-r, y1], fill=fill)
    draw.rectangle([x0, y0+r, x1, y1-r], fill=fill)
    for cx, cy in [(x0, y0), (x1-2*r, y0), (x0, y1-2*r), (x1-2*r, y1-2*r)]:
        draw.ellipse([cx, cy, cx+2*r, cy+2*r], fill=fill)

def darken(c, factor=0.75):
    return tuple(max(0, int(v * factor)) for v in c)

def lighten(c, factor=1.3):
    return tuple(min(255, int(v * factor)) for v in c)

def make_card(topic: dict, output_path: str, handle: str = "@fernandomagalhaescoutinho"):
    W = H = 1080
    PAD = 60

    cor = topic.get("cor", "#0C447C")
    pal = PALETTES.get(cor, PALETTES["#0C447C"])
    bg1, bg2 = pal["bg"], pal["bg2"]

    WHITE     = (255, 255, 255)
    WHITE_60  = (180, 205, 228)
    WHITE_35  = (140, 170, 200)

    img = Image.new("RGB", (W, H), bg1)
    draw_gradient(img, bg1, bg2)
    draw = ImageDraw.Draw(img)

    # Decorative background circle (top-right)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.ellipse([W-60, -100, W+340, 340], fill=(255, 255, 255, 14))
    img.paste(Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB"))
    draw = ImageDraw.Draw(img)

    # ── BADGES ────────────────────────────────────────────────────────────────
    badge_font = load_font(30)
    bh = 54
    for text, x_start in [("AMIB", PAD), ("TEMI", W - PAD - 116)]:
        rounded_rect(draw, [x_start, PAD, x_start + 116, PAD + bh], 10, darken(bg1, 0.80))
        bb = draw.textbbox((0, 0), text, font=badge_font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        draw.text((x_start + (116 - tw) // 2, PAD + (bh - th) // 2), text,
                  font=badge_font, fill=WHITE if text == "AMIB" else WHITE_60)

    # ── SUBTÍTULO ─────────────────────────────────────────────────────────────
    sub_font = load_font(27, bold=False)
    sub_y = PAD + bh + 48
    draw.text((PAD, sub_y), topic.get("subtitulo", "").upper(), font=sub_font, fill=WHITE_60)

    # ── TÍTULO ────────────────────────────────────────────────────────────────
    title_font = load_font(72)
    titulo = topic.get("titulo", "")
    title_y = sub_y + 46

    # word-wrap title to fit width
    max_w = W - 2 * PAD
    words = titulo.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bb = draw.textbbox((0, 0), test, font=title_font)
        if bb[2] - bb[0] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)

    title_end_y = title_y
    for line in lines:
        draw.text((PAD, title_end_y), line, font=title_font, fill=WHITE)
        bb = draw.textbbox((0, 0), line, font=title_font)
        title_end_y += bb[3] - bb[1] + 6

    # ── DIVIDER ───────────────────────────────────────────────────────────────
    div_y = title_end_y + 32
    draw.rectangle([PAD, div_y, PAD + 80, div_y + 5], fill=lighten(bg1, 1.6))

    # ── PONTOS ────────────────────────────────────────────────────────────────
    pt_font   = load_font(28, bold=False)
    num_font  = load_font(24)
    y         = div_y + 38
    NUM_R     = 22
    CARD_R    = W - PAD

    for i, ponto in enumerate(topic.get("pontos", [])):
        if y > H - 120: break

        wrapped_lines = textwrap.fill(ponto, width=40).split("\n")
        line_h = draw.textbbox((0, 0), "Ag", font=pt_font)[3] + 5
        box_h = max(len(wrapped_lines) * line_h + 28, NUM_R * 2 + 20)

        # pill background
        rounded_rect(draw, [PAD, y, CARD_R, y + box_h], 14, darken(bg1, 0.82))

        # number circle
        ncx, ncy = PAD + NUM_R + 8, y + box_h // 2
        draw.ellipse([ncx-NUM_R, ncy-NUM_R, ncx+NUM_R, ncy+NUM_R], fill=lighten(bg1, 1.25))
        ns = str(i + 1)
        nbb = draw.textbbox((0, 0), ns, font=num_font)
        draw.text((ncx - (nbb[2]-nbb[0])//2, ncy - (nbb[3]-nbb[1])//2),
                  ns, font=num_font, fill=WHITE)

        # text lines
        tx, ty = PAD + NUM_R * 2 + 22, y + (box_h - len(wrapped_lines) * line_h) // 2
        for ln in wrapped_lines:
            draw.text((tx, ty), ln, font=pt_font, fill=(230, 240, 255))
            ty += line_h

        y += box_h + 10

    # ── FOOTER ────────────────────────────────────────────────────────────────
    foot_font = load_font(28, bold=False)
    logo_font = load_font(22, bold=False)
    draw.text((PAD, H - 76), handle, font=foot_font, fill=WHITE_60)
    logo = "Medicina Intensiva"
    lbb = draw.textbbox((0, 0), logo, font=logo_font)
    draw.text((W - PAD - (lbb[2]-lbb[0]), H - 70), logo, font=logo_font, fill=WHITE_35)

    img.save(output_path, "PNG", optimize=True)
    print(f"Saved: {output_path}", file=sys.stderr)
    return output_path


if __name__ == "__main__":
    topics = json.loads((SCRIPT_DIR / "topics.json").read_text())
    topic_id = sys.argv[1] if len(sys.argv) > 1 else "sepse"
    output   = sys.argv[2] if len(sys.argv) > 2 else "/tmp/instagram-card.png"
    topic = next((t for t in topics if t["id"] == topic_id), topics[0])
    make_card(topic, output)
    print(output)
