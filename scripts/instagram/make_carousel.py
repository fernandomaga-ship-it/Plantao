#!/usr/bin/env python3
"""
Gera um carrossel de slides 1080x1080 para Instagram.
Uso: python3 make_carousel.py <carousel_id>

Saída: assets/instagram/carousel/<carousel_id>/slide_01.png ... slide_N.png
       Retorna no stdout os caminhos, um por linha.
"""
import sys, json, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).parent
OUT_BASE   = Path(__file__).parent.parent.parent / "assets" / "instagram"

# ── Fontes ─────────────────────────────────────────────────────────────────────
FONTS_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONTS_REG  = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
] + FONTS_BOLD

def font(size, bold=True):
    for p in (FONTS_BOLD if bold else FONTS_REG):
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

# ── Gradiente ──────────────────────────────────────────────────────────────────
def gradient(img, c1, c2):
    d = ImageDraw.Draw(img)
    for y in range(img.height):
        t = y / img.height
        d.line([(0,y),(img.width,y)],
               fill=tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3)))

# ── Rect arredondado ──────────────────────────────────────────────────────────
def rrect(d, xy, r, fill):
    x0,y0,x1,y1 = xy
    d.rectangle([x0+r,y0,x1-r,y1], fill=fill)
    d.rectangle([x0,y0+r,x1,y1-r], fill=fill)
    for cx,cy in [(x0,y0),(x1-2*r,y0),(x0,y1-2*r),(x1-2*r,y1-2*r)]:
        d.ellipse([cx,cy,cx+2*r,cy+2*r], fill=fill)

def dk(c, f=0.78): return tuple(max(0,int(v*f)) for v in c)
def lt(c, f=1.35): return tuple(min(255,int(v*f)) for v in c)

W = H = 1080
PAD = 58

# ── CAPA ───────────────────────────────────────────────────────────────────────
def make_cover(data: dict, out: Path):
    bg1 = data["cor1"]; bg2 = data["cor2"]
    img = Image.new("RGB", (W,H), bg1)
    gradient(img, bg1, bg2)
    d = ImageDraw.Draw(img)

    WHITE = (255,255,255); W60 = (190,210,230); W30 = (130,160,185)

    # círculo decorativo
    ov = Image.new("RGBA",(W,H),(0,0,0,0))
    od = ImageDraw.Draw(ov)
    od.ellipse([W-180,-180,W+280,280], fill=(*lt(bg1),18))
    img.paste(Image.alpha_composite(img.convert("RGBA"),ov).convert("RGB"))
    d = ImageDraw.Draw(img)

    # badge AMIB / TEMI
    bf = font(28); bh = 52
    for txt, x in [("AMIB", PAD), ("TEMI", W-PAD-110)]:
        rrect(d,[x,PAD,x+110,PAD+bh],10,dk(bg1,0.82))
        bb = d.textbbox((0,0),txt,font=bf)
        d.text((x+(110-bb[2]+bb[0])//2, PAD+(bh-bb[3]+bb[1])//2),
               txt, font=bf, fill=WHITE if txt=="AMIB" else W60)

    # número do slide
    slide_f = font(24, bold=False)
    slide_txt = f"1 / {data['total']}"
    bb = d.textbbox((0,0),slide_txt,font=slide_f)
    d.text((W-PAD-(bb[2]-bb[0]), PAD+(bh-bb[3]+bb[1])//2+2),
           slide_txt, font=slide_f, fill=W30)

    # categoria
    cat_f = font(26, bold=False)
    d.text((PAD, PAD+bh+50), data.get("categoria","NEUROINTENSIVISMO").upper(),
           font=cat_f, fill=W60)

    # título (grande)
    tf = font(80)
    titulo = data["titulo"]
    words = titulo.split(); lines = []; cur=""
    for w in words:
        test=(cur+" "+w).strip()
        if d.textbbox((0,0),test,font=tf)[2] <= W-2*PAD: cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)

    ty = PAD+bh+105
    for ln in lines:
        d.text((PAD,ty), ln, font=tf, fill=WHITE)
        ty += d.textbbox((0,0),ln,font=tf)[3]+6

    # subtítulo
    sf = font(34, bold=False)
    ty += 10
    d.text((PAD,ty), data["subtitulo"], font=sf, fill=W60)
    ty += d.textbbox((0,0),data["subtitulo"],font=sf)[3]+36

    # divider
    d.rectangle([PAD,ty,PAD+80,ty+5], fill=lt(bg1,1.7))
    ty += 28

    # tópicos em pills
    pf = font(25, bold=False); gutter=10; x=PAD
    for tp in data.get("topicos",[]):
        bb = d.textbbox((0,0),tp,font=pf)
        pw = bb[2]-bb[0]+28; ph = bb[3]-bb[1]+16
        if x+pw > W-PAD: x=PAD; ty+=ph+gutter
        rrect(d,[x,ty,x+pw,ty+ph],ph//2,dk(bg1,0.80))
        d.text((x+14,ty+8), tp, font=pf, fill=W60)
        x += pw+gutter

    # seta "deslize"
    af = font(26, bold=False)
    arr = "deslize →"
    ab = d.textbbox((0,0),arr,font=af)
    d.text((W-PAD-(ab[2]-ab[0]), H-66), arr, font=af, fill=W30)

    # handle
    hf = font(26, bold=False)
    d.text((PAD, H-70), data.get("handle","@fernandomagalhaescoutinho"),
           font=hf, fill=W60)

    img.save(out, "PNG"); print(str(out), file=sys.stderr)

# ── SLIDE DE CONTEÚDO ──────────────────────────────────────────────────────────
def make_slide(slide: dict, num: int, total: int, bg1, bg2, out: Path):
    img = Image.new("RGB",(W,H),bg1)
    gradient(img,bg1,bg2)
    d = ImageDraw.Draw(img)

    WHITE=(255,255,255); W60=(190,210,230); W30=(130,160,185)

    # círculo decorativo
    ov = Image.new("RGBA",(W,H),(0,0,0,0))
    od = ImageDraw.Draw(ov)
    od.ellipse([W-120,-120,W+320,320], fill=(*lt(bg1),12))
    img.paste(Image.alpha_composite(img.convert("RGBA"),ov).convert("RGB"))
    d = ImageDraw.Draw(img)

    # AMIB badge + número slide
    bf = font(28); bh = 50
    rrect(d,[PAD,PAD,PAD+110,PAD+bh],10,dk(bg1,0.82))
    bb=d.textbbox((0,0),"AMIB",font=bf)
    d.text((PAD+(110-bb[2]+bb[0])//2, PAD+(bh-bb[3]+bb[1])//2),
           "AMIB", font=bf, fill=WHITE)

    sf2 = font(26, bold=False)
    snum = f"{num} / {total}"
    sb = d.textbbox((0,0),snum,font=sf2)
    d.text((W-PAD-(sb[2]-sb[0]), PAD+(bh-sb[3]+sb[1])//2+2),
           snum, font=sf2, fill=W30)

    # subtítulo (categoria do slide)
    cf = font(24, bold=False)
    d.text((PAD, PAD+bh+36), slide.get("categoria","").upper(), font=cf, fill=W60)

    # título
    tf = font(60)
    titulo = slide["titulo"]
    words=titulo.split(); lines=[]; cur=""
    for w in words:
        test=(cur+" "+w).strip()
        if d.textbbox((0,0),test,font=tf)[2] <= W-2*PAD: cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)

    ty = PAD+bh+82
    for ln in lines:
        d.text((PAD,ty),ln,font=tf,fill=WHITE)
        ty += d.textbbox((0,0),ln,font=tf)[3]+4
    ty += 22

    # divider
    d.rectangle([PAD,ty,PAD+70,ty+4], fill=lt(bg1,1.6))
    ty += 26

    # pontos
    pf  = font(27, bold=False)
    nf  = font(22)
    NR  = 20; gap = 8

    for i, ponto in enumerate(slide.get("pontos",[])):
        if ty > H-100: break
        wlines = textwrap.fill(ponto, width=38).split("\n")
        lh = d.textbbox((0,0),"Ag",font=pf)[3]+5
        bh2 = max(len(wlines)*lh+24, NR*2+16)

        rrect(d,[PAD,ty,W-PAD,ty+bh2],12,dk(bg1,0.82))

        ncx = PAD+NR+8; ncy = ty+bh2//2
        d.ellipse([ncx-NR,ncy-NR,ncx+NR,ncy+NR], fill=lt(bg1,1.25))
        ns=str(i+1)
        nb=d.textbbox((0,0),ns,font=nf)
        d.text((ncx-(nb[2]-nb[0])//2, ncy-(nb[3]-nb[1])//2), ns, font=nf, fill=WHITE)

        tx=PAD+NR*2+18; tty=ty+(bh2-len(wlines)*lh)//2
        for ln in wlines:
            d.text((tx,tty),ln,font=pf,fill=(225,240,255))
            tty+=lh
        ty += bh2+gap

    # rodapé
    hf2 = font(24, bold=False)
    d.text((PAD,H-66), slide.get("handle","@fernandomagalhaescoutinho"),
           font=hf2, fill=W60)

    # seta (exceto último slide)
    if num < total:
        af=font(24, bold=False)
        arr="→ mais"
        ab=d.textbbox((0,0),arr,font=af)
        d.text((W-PAD-(ab[2]-ab[0]),H-66),arr,font=af,fill=W30)

    img.save(out,"PNG"); print(str(out), file=sys.stderr)


# ── CARROSSÉIS ─────────────────────────────────────────────────────────────────
CAROUSELS = {
  "hemorragia-cerebral": {
    "cor1": (100, 15, 15),
    "cor2": (60,  6,  6),
    "handle": "@fernandomagalhaescoutinho",
    "cover": {
      "titulo": "Hemorragia Cerebral",
      "subtitulo": "Manejo Neurointensivo na UTI",
      "categoria": "Neurointensivismo",
      "topicos": ["Tipos", "Escalas", "Neuroproteção", "HIC", "Vasoespasmo", "Monitorização"]
    },
    "slides": [
      {
        "titulo": "Tipos de Sangramento",
        "categoria": "Epidemiologia",
        "pontos": [
          "HSA: ruptura de aneurisma — mortalidade 30–40% em 30 dias",
          "HIC espontânea: HAS (50%), angiopatia amiloide, anticoagulação",
          "HSD agudo: trauma — cirurgia se > 10 mm ou desvio > 5 mm",
          "HED: art. meníngea média — intervalo lúcido + deterioração rápida",
          "Contusão cerebral: monitorar expansão nas primeiras 24h"
        ]
      },
      {
        "titulo": "Escalas de Classificação",
        "categoria": "Diagnóstico",
        "pontos": [
          "Hunt & Hess (HSA): I assintomático → V coma/descerebração",
          "Fisher (TC na HSA): grau 3 (coágulo ≥ 1 mm) = maior risco de vasoespasmo",
          "ICH Score (HIC): GCS + volume > 30 mL + infratentorial + IV + idade > 80",
          "ICH Score 0–1 = mortalidade < 20%; ≥ 4 = mortalidade > 80%",
          "GCS ≤ 8 em qualquer sangramento → intubação para proteção de via aérea"
        ]
      },
      {
        "titulo": "Neuroproteção",
        "categoria": "Suporte Intensivo",
        "pontos": [
          "HOB 30° — reduz PIC e melhora drenagem venosa cerebral",
          "Normotermia (< 37,5 °C) — hipertermia agrava dano neuronal secundário",
          "Normoglicemia 80–180 mg/dL — hipoglicemia é o maior risco",
          "Normocapnia PaCO2 35–45 mmHg — hipocapnia causa vasoconstrição",
          "SaO2 > 94% — hipóxia piora o metabolismo cerebral lesionado"
        ]
      },
      {
        "titulo": "Manejo da HIC",
        "categoria": "HIC · PIC > 20 mmHg",
        "pontos": [
          "Meta PPC 60–70 mmHg (PPC = PAM − PIC); PIC normal < 15 mmHg",
          "1ª linha: HOB 30° + sedoanalgesia + normocapnia + DVE",
          "Osmoterapia: Manitol 0,5–1 g/kg IV (osmol < 320) OU NaCl 3% 150 mL",
          "Hiperventilação transitória (PaCO2 30–35) só como ponte — máx 30 min",
          "Refratário: craniectomia descompressiva ou coma barbitúrico"
        ]
      },
      {
        "titulo": "Vasoespasmo Pós-HSA",
        "categoria": "Complicação · Dias 4–14",
        "pontos": [
          "Pico: 7–10 dias após HSA — isquemia cerebral tardia (DCI)",
          "Nimodipino 60 mg 4/4h por 21 dias — TODOS os pacientes com HSA",
          "Diagnóstico: DTC — ACM > 120 cm/s (grave > 200 cm/s)",
          "Índice de Lindegaard > 3 diferencia vasoespasmo de hiperfluxo",
          "Vasoespasmo sintomático: hipertensão induzida ± angioplastia transluminal"
        ]
      },
      {
        "titulo": "Monitorização Avançada",
        "categoria": "PIC · DTC · Pletismografia",
        "pontos": [
          "DVE (derivação ventricular externa): gold standard para PIC + drena LCR",
          "Doppler transcraniano (DTC): IP (índice de pulsatilidade) normal < 1,2",
          "Pletismografia cerebral (NIRS/SrO2): alerta de hipoperfusão regional",
          "SjO2 (bulbo jugular): normal 55–75%; < 50% = isquemia; > 75% = hiperemia",
          "bEEG contínuo: detectar crises eletrográficas subclínicas (status não-conv.)"
        ]
      }
    ]
  }
}

# ── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    carousel_id = sys.argv[1] if len(sys.argv) > 1 else "hemorragia-cerebral"
    data = CAROUSELS.get(carousel_id)
    if not data:
        print(f"Carrossel '{carousel_id}' não encontrado.", file=sys.stderr)
        sys.exit(1)

    out_dir = OUT_BASE / "carousel" / carousel_id
    out_dir.mkdir(parents=True, exist_ok=True)

    slides    = data["slides"]
    total     = len(slides) + 1  # +1 para a capa
    bg1, bg2  = data["cor1"], data["cor2"]
    handle    = data.get("handle","@fernandomagalhaescoutinho")

    # Capa
    cover_out = out_dir / "slide_01.png"
    make_cover({**data["cover"], "cor1":bg1, "cor2":bg2, "total":total, "handle":handle}, cover_out)
    print(str(cover_out))

    # Slides
    for i, slide in enumerate(slides, start=2):
        slide_out = out_dir / f"slide_{i:02d}.png"
        make_slide({**slide, "handle":handle}, i, total, bg1, bg2, slide_out)
        print(str(slide_out))

    print(f"\n✅ {total} slides gerados em {out_dir}", file=sys.stderr)
