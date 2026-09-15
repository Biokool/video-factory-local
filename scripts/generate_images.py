"""
Generador de imagenes V6 - multi-fotograma, investigacion automatica.

Cambios vs V5:
- La mano ya NO se dibuja: se compone la FOTO real CC0 (assets/hands/hand_base.png)
  con alfa feathered, auto-calibrada (bbox + lado del pulgar desde la mascara).
- Cada escena genera N keyframes con progresion visual (lineas que se dibujan,
  puntos que aparecen, labels con fade).
- Si research.json trae conceptos, se agrega un panel lateral con la foto
  investigada (manzana/cosmos/sol/...) y su etiqueta.

Salida:
  data/images/scene_XXX/f_YYY.png  (keyframes)
  data/jobs/<jid>/images.json      (indice de keyframes)

Uso:
  python generate_images.py --storyboard ... --research ... --frames 7
"""
import sys, os, json, math, random, argparse, cairo
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFilter, ImageOps

SCRIPT_DIR = Path(__file__).resolve().parent.parent
HAND_PATH = SCRIPT_DIR / "assets" / "hands" / "hand_base.png"
IMAGES_DIR = SCRIPT_DIR / "data" / "images"

LCOL = {
    "corazon": (0/255, 200/255, 220/255), "cabeza": (0/255, 180/255, 100/255),
    "destino": (230/255, 120/255, 30/255), "vida": (200/255, 50/255, 80/255),
}
MCOL = {
    "mercurio": (230/255, 60/255, 160/255), "sol": (230/255, 60/255, 60/255),
    "saturno": (240/255, 150/255, 40/255), "jupiter": (240/255, 210/255, 50/255),
    "venus": (250/255, 120/255, 150/255),
}
SCFG = {
    1: {"title": "LECTURA DE MANO", "subtitle": "La Linea de la Vida", "hl": "vida"},
    2: {"title": "PUNTOS DE PARTIDA", "subtitle": "Tres origenes posibles", "hl": "vida"},
    3: {"title": "FORMA DEL NACIMIENTO", "subtitle": "Curva amplia vs estrecha", "hl": "vida"},
    4: {"title": "PROFUNDIDAD Y VITALIDAD", "subtitle": "Lo que la linea revela", "hl": "vida"},
}

# Anclas normalizadas al bbox de la mano con pulgar a la DERECHA.
# Se espejan en X si el pulgar detectado queda a la izquierda.
PALM = {
    "vida":    [(0.60, 0.50), (0.42, 0.66), (0.36, 0.80), (0.40, 0.93)],
    "cabeza":  [(0.58, 0.58), (0.44, 0.62), (0.30, 0.64), (0.16, 0.66)],
    "corazon": [(0.16, 0.50), (0.30, 0.46), (0.44, 0.43), (0.58, 0.41)],
    "destino": [(0.42, 0.44), (0.40, 0.58), (0.37, 0.74), (0.37, 0.90)],
}
MONTES = {
    "venus":    (0.68, 0.74, 0.085),
    "jupiter":  (0.52, 0.44, 0.045),
    "saturno":  (0.40, 0.42, 0.045),
    "sol":      (0.28, 0.45, 0.045),
    "mercurio": (0.17, 0.49, 0.045),
}
DASH = {"corazon": [8, 4], "cabeza": [4, 4], "destino": [12, 4, 4, 4], "vida": [10, 5]}


def bez3(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n; u = 1 - t
        x = u**3*p0[0] + 3*u**2*t*p1[0] + 3*u*t**2*p2[0] + t**3*p3[0]
        y = u**3*p0[1] + 3*u**2*t*p1[1] + 3*u*t**2*p2[1] + t**3*p3[1]
        out.append((x, y))
    return out


def _set_font(ctx, size, bold=False):
    ctx.select_font_face("Segoe UI",
                         cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)


def _rrect(ctx, x, y, w, h, r):
    ctx.new_path()
    ctx.move_to(x + r, y); ctx.line_to(x + w - r, y)
    ctx.arc(x + w - r, y + r, r, -math.pi/2, 0)
    ctx.line_to(x + w, y + h - r)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi/2)
    ctx.line_to(x + r, y + h)
    ctx.arc(x + r, y + h - r, r, math.pi/2, math.pi)
    ctx.line_to(x, y + r)
    ctx.arc(x + r, y + r, r, math.pi, 3*math.pi/2)
    ctx.close_path()


def draw_partial(ctx, pts, frac, color, lw=5, dash=None, glow=False):
    """Dibuja la polilinea pts hasta la fraccion frac (0-1)."""
    if frac <= 0 or len(pts) < 2:
        return
    n = max(2, int(len(pts) * min(1.0, frac)) + 1)
    sub = pts[:n]
    if glow:
        # glow más intenso: 4 capas con diferentes anchos y opacidades
        for gw, a in [(lw*5, .12), (lw*3.5, .20), (lw*2.2, .30), (lw*1.4, .45)]:
            ctx.set_source_rgba(min(1, color[0]+.3), min(1, color[1]+.3),
                                min(1, color[2]+.3), a)
            ctx.set_line_width(gw); ctx.set_dash([])
            ctx.move_to(*sub[0])
            for p in sub[1:]: ctx.line_to(*p)
            ctx.stroke()
    ctx.set_source_rgb(*color); ctx.set_line_width(lw)
    ctx.set_dash(dash or [])
    ctx.move_to(*sub[0])
    for p in sub[1:]: ctx.line_to(*p)
    ctx.stroke(); ctx.set_dash([])


def draw_pulsing_point(ctx, x, y, color, phase, base_r=12):
    for gw, a in [(base_r*2.2, .18), (base_r*1.6, .30)]:
        ctx.set_source_rgba(color[0], color[1], color[2], a * (1 - phase*.5))
        ctx.arc(x, y, gw * (0.8 + phase*.4), 0, 6.283); ctx.fill()
    ctx.set_source_rgb(*color); ctx.arc(x, y, base_r, 0, 6.283); ctx.fill()
    ctx.set_source_rgb(1, 1, 1); ctx.set_line_width(3)
    ctx.arc(x, y, base_r, 0, 6.283); ctx.stroke()


def _label(ctx, lx, ly, tx, ty, text, fs=16, col=(1, 1, 1), alpha=1.0):
    if alpha <= 0.02:
        return
    _set_font(ctx, fs, True)
    ext = ctx.text_extents(text)
    tw, th = ext.width, ext.height
    pad = 8
    # fondo sólido semi-transparente
    ctx.set_source_rgba(0, 0, 0, .85 * alpha)
    _rrect(ctx, lx - pad, ly - pad, tw + 2*pad, th + 2*pad + 4, 6); ctx.fill()
    # borde sutil
    ctx.set_source_rgba(1, 1, 1, .25 * alpha)
    ctx.set_line_width(1)
    _rrect(ctx, lx - pad, ly - pad, tw + 2*pad, th + 2*pad + 4, 6); ctx.stroke()
    # texto
    ctx.set_source_rgba(col[0], col[1], col[2], alpha)
    ctx.move_to(lx, ly + th); ctx.show_text(text)
    # línea punteada al punto
    ctx.set_line_width(1.5); ctx.set_source_rgba(.7, .7, .85, .6 * alpha)
    ctx.set_dash([4, 4])
    ctx.move_to(lx + tw/2, ly + th + pad)
    ctx.line_to(tx, ty); ctx.stroke(); ctx.set_dash([])
    # punto final
    ctx.set_source_rgba(1, 1, 1, .8 * alpha)
    ctx.arc(tx, ty, 5, 0, 6.283); ctx.fill()
    ctx.set_source_rgba(col[0], col[1], col[2], alpha)
    ctx.arc(tx, ty, 3, 0, 6.283); ctx.fill()


def draw_title(ctx, w, h, cfg, alpha=1.0):
    _set_font(ctx, max(34, w // 30), True)
    ext = ctx.text_extents(cfg["title"])
    ctx.set_source_rgba(1, 1, 1, alpha)
    ctx.move_to((w - ext.width) / 2, 52); ctx.show_text(cfg["title"])
    _set_font(ctx, max(18, w // 55))
    ext = ctx.text_extents(cfg["subtitle"])
    ctx.set_source_rgba(.71, .63, .86, alpha)
    ctx.move_to((w - ext.width) / 2, 80); ctx.show_text(cfg["subtitle"])
    ctx.set_source_rgba(1, 1, 1, .25 * alpha); ctx.set_line_width(2)
    uw = min(600, w // 3)
    ctx.move_to(w/2 - uw/2, 92); ctx.line_to(w/2 + uw/2, 92); ctx.stroke()


def draw_footer(ctx, w, h, sid, tot):
    ctx.set_source_rgba(0, 0, 0, .55)
    ctx.rectangle(0, h - 46, w, 46); ctx.fill()
    _set_font(ctx, max(13, w // 70))
    txt = "QUIROMANCIA TERAPEUTICA - CONTENIDO EDUCATIVO"
    ext = ctx.text_extents(txt)
    ctx.set_source_rgb(.47, .43, .59)
    ctx.move_to((w - ext.width) / 2, h - 20); ctx.show_text(txt)
    num = f"{sid}/{tot}"
    ext = ctx.text_extents(num)
    ctx.set_source_rgb(.39, .35, .51)
    ctx.move_to(w - ext.width - 20, h - 20); ctx.show_text(num)


# == Fondo espacial (cacheado en disco) ==
def build_space_bg(w, h) -> Image.Image:
    cache = IMAGES_DIR / "_bg_space.png"
    if cache.exists():
        im = Image.open(cache)
        if im.size == (w, h):
            return im.convert("RGB")
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    for y in range(h):
        r = y / h
        ctx.set_source_rgb(.03 + .07*r, .02 + .03*r, .11 + .17*r)
        ctx.move_to(0, y); ctx.line_to(w, y); ctx.stroke()
    random.seed(42)
    for _ in range(320):
        x, y = random.randint(0, w), random.randint(0, h)
        b = random.random()*.6 + .4
        ctx.set_source_rgb(b, b, b)
        ctx.arc(x, y, random.choice([1, 1, 1, 1.5, 2]), 0, 6.283); ctx.fill()
    for _ in range(4):
        x, y = random.randint(0, w), random.randint(0, h)
        g = cairo.RadialGradient(x, y, 0, x, y, 180)
        g.add_color_stop_rgba(.6, .12, .10, .25, .5)
        g.add_color_stop_rgba(1, .12, .10, .25, 0)
        ctx.set_source(g); ctx.arc(x, y, 180, 0, 6.283); ctx.fill()
    surf.write_to_png(str(cache))
    return Image.open(cache).convert("RGB")


# == Calibracion de la mano foto ==
class HandPhoto:
    """Carga hand_base.png, detecta bbox y lado del pulgar via alfa."""

    def __init__(self, path: Path):
        self.im = Image.open(path).convert("RGBA")
        a = self.im.getchannel("A")
        px = a.load()
        w, h = self.im.size
        xs, ys = [], []
        step = 4
        for y in range(0, h, step):
            for x in range(0, w, step):
                if px[x, y] > 120:
                    xs.append(x); ys.append(y)
        if not xs:
            raise RuntimeError("mano sin contenido (mascara vacia)")
        self.bbox = (min(xs), min(ys), max(xs), max(ys))
        bw = self.bbox[2] - self.bbox[0]
        bh = self.bbox[3] - self.bbox[1]
        y0 = self.bbox[1] + int(bh * 0.50)
        y1 = self.bbox[1] + int(bh * 0.75)
        lx = [x for x, y in zip(xs, ys) if y0 <= y <= y1]
        cx = (self.bbox[0] + self.bbox[2]) / 2
        if lx:
            self.thumb_right = (max(lx) - cx) >= (cx - min(lx))
        else:
            self.thumb_right = True
        print(f"  [mano] bbox={self.bbox} pulgar={'derecha' if self.thumb_right else 'izquierda'}")

    def resized(self, target_h: int) -> Image.Image:
        b = self.bbox
        crop = self.im.crop(b)
        ratio = target_h / crop.height
        return crop.resize((int(crop.width * ratio), target_h), Image.LANCZOS)

    def resized_filled(self, target_h: int) -> Image.Image:
        """Devuelve la mano con silueta rellena de tono piel (RGBA)."""
        raw = self.resized(target_h)
        a = raw.getchannel("A")
        # Dilatar FUERTE para cerrar todos los huecos entre líneas
        dilated = a.filter(ImageFilter.MaxFilter(7))
        dilated = dilated.filter(ImageFilter.MaxFilter(5))
        dilated = dilated.filter(ImageFilter.GaussianBlur(2))
        # Elevar alpha para que la piel sea casi sólida en el centro
        dilated = dilated.point(lambda v: min(255, int(v * 2.0) + 80))
        # Crear capa opaca de piel cálida
        skin = Image.new("RGBA", raw.size, (224, 182, 150, 255))
        skin.putalpha(dilated)
        # Pegar las líneas del dibujo original encima
        skin.paste(raw, (0, 0), raw)
        return skin

    def anchors(self, box):
        """box=(x,y,w,h) en pantalla. Devuelve lineas/montes en px, espejando si hace falta."""
        x, y, w, h = box
        mir = (lambda p: (1 - p[0], p[1])) if not self.thumb_right else (lambda p: p)
        lines = {}
        for name, cps in PALM.items():
            pts = bez3(*[mir(c) for c in cps])
            lines[name] = [(x + px * w, y + py * h) for px, py in pts]
        montes = {}
        for name, (mx, my, mr) in MONTES.items():
            if not self.thumb_right:
                mx = 1 - mx
            montes[name] = (x + mx * w, y + my * h, mr * w)
        return lines, montes


# == Panel de concepto investigado ==
def paste_concept_panel(base: Image.Image, photo_path: str, caption: str,
                        alpha: float, slot=(0.685, 0.16, 0.27, 0.56)):
    """Pega panel redondeado con foto cover-crop + caption. slot=(x,y,w,h) fraccionales."""
    if alpha <= 0.02:
        return
    W, H = base.size
    px_, py_, pw, ph = int(slot[0]*W), int(slot[1]*H), int(slot[2]*W), int(slot[3]*H)
    photo = Image.open(photo_path).convert("RGB")
    pr = max(pw / photo.width, ph / photo.height)
    nw, nh = int(photo.width * pr) + 1, int(photo.height * pr) + 1
    photo = photo.resize((nw, nh), Image.LANCZOS)
    photo = photo.crop(((nw - pw)//2, (nh - ph)//2, (nw - pw)//2 + pw, (nh - ph)//2 + ph))
    photo = ImageOps.autocontrast(photo, cutoff=1)
    dark = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    ImageDraw.Draw(dark).rectangle([0, 0, pw, ph], fill=(10, 6, 25, 140))
    photo = Image.alpha_composite(photo.convert("RGBA"), dark)
    if alpha < 1:
        a = photo.getchannel("A").point(lambda v: int(v * alpha))
        photo.putalpha(a)
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=18, fill=255)
    base.paste(photo, (px_, py_), mask)
    # caption
    csurf = cairo.ImageSurface(cairo.FORMAT_ARGB32, pw, 44)
    cctx = cairo.Context(csurf)
    _set_font(cctx, 20, True)
    ext = cctx.text_extents(caption)
    cctx.set_source_rgba(1, 1, 1, alpha)
    cctx.move_to((pw - ext.width) / 2, 30); cctx.show_text(caption)
    cap = Image.frombuffer("RGBA", (pw, 44), csurf.get_data(), "raw", "BGRA", 0, 1)
    base.paste(cap, (px_, py_ + ph - 52), cap)


# == Composicion de un keyframe ==
def render_frame(scene, hand, concept_infos, ki, nk, W, H, sid, tot, cfg):
    prog = ki / max(1, nk - 1)  # 0..1 progreso de la escena
    base = build_space_bg(W, H).convert("RGBA").copy()

    # mano con color de piel (silueta rellena + líneas encima)
    hand_h = int(H * (0.66 if sid == 3 else 0.72))
    hand_im = hand.resized_filled(hand_h)

    if sid == 3:
        # dos manos lado a lado
        boxes = []
        gap = int(W * 0.02)
        total_w = hand_im.width * 2 + gap
        x0 = (W - total_w) // 2
        for i in range(2):
            bx = x0 + i * (hand_im.width + gap)
            by = int(H * 0.22)
            base.alpha_composite(hand_im, (bx, by))
            boxes.append((bx, by, hand_im.width, hand_h))
    else:
        hx = int(W * 0.36) - hand_im.width // 2
        hy = int(H * 0.20)
        base.alpha_composite(hand_im, (hx, hy))
        boxes = [(hx, hy, hand_im.width, hand_h)]

    # convertir PIL -> cairo via buffer
    data = bytearray(base.tobytes("raw", "BGRA"))
    surf = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    hl = cfg["hl"]
    title_a = min(1.0, prog * 4)

    if sid == 1:
        box = boxes[0]
        lines, montes = hand.anchors(box)
        # revelado secuencial de lineas: corazon -> cabeza -> destino -> vida
        order = ["corazon", "cabeza", "destino", "vida"]
        for i, name in enumerate(order):
            start = 0.08 + i * 0.18
            frac = max(0.0, min(1.0, (prog - start) / 0.20))
            draw_partial(ctx, lines[name], frac, LCOL[name],
                         lw=8 if name == hl else 5, dash=DASH[name], glow=(name == hl))
        # montes con fade — más grandes y brillantes
        ma = max(0.0, min(1.0, (prog - 0.50) / 0.2))
        if ma > 0:
            for name, (mx, my, mr) in montes.items():
                c = MCOL[name]
                # halo exterior
                ctx.set_source_rgba(c[0]*.3, c[1]*.3, c[2]*.3, .5 * ma)
                ctx.arc(mx, my, mr * 1.8, 0, 6.283); ctx.fill()
                # círculo principal
                ctx.set_source_rgba(c[0], c[1], c[2], .85 * ma)
                ctx.arc(mx, my, mr * (0.5 + 0.5 * ma), 0, 6.283); ctx.fill()
                # borde blanco
                ctx.set_source_rgba(1, 1, 1, .9 * ma)
                ctx.set_line_width(3); ctx.arc(mx, my, mr * (0.5 + 0.5 * ma), 0, 6.283); ctx.stroke()
        # labels al final — más grandes y con fondo sólido
        la = max(0.0, min(1.0, (prog - 0.72) / 0.2))
        if la > 0:
            _label(ctx, box[0] + box[2] + 25, box[1] + 30,
                   *reversed_point(montes["venus"][:2]), "Monte de Venus", 17, alpha=la)
            _label(ctx, box[0] - 280, box[1] + 60,
                   *reversed_point(lines["vida"][len(lines["vida"])//2]), "Linea de la Vida",
                   17, col=LCOL["vida"], alpha=la)
            _label(ctx, box[0] - 280, box[1] + 120,
                   *reversed_point(lines["corazon"][len(lines["corazon"])//2]),
                   "Linea del Corazon", 17, col=LCOL["corazon"], alpha=la)
            _label(ctx, box[0] - 280, box[1] + 180,
                   *reversed_point(lines["cabeza"][len(lines["cabeza"])//2]),
                   "Linea de la Cabeza", 17, col=LCOL["cabeza"], alpha=la)
            _label(ctx, box[0] + box[2] + 25, box[1] + 100,
                   *reversed_point(montes["jupiter"][:2]), "Monte de Jupiter", 17, alpha=la)
            _label(ctx, box[0] + box[2] + 25, box[1] + 170,
                   *reversed_point(montes["saturno"][:2]), "Monte de Saturno", 17, alpha=la)

    elif sid == 2:
        box = boxes[0]
        lines, montes = hand.anchors(box)
        vida = lines["vida"]
        draw_partial(ctx, vida, min(1.0, prog * 2.5), LCOL["vida"], lw=6, dash=DASH["vida"], glow=True)
        # puntos 1,2,3 aparecen secuencialmente
        p_fracs = [0.02, 0.10, 0.18]
        cols = [(0, 220/255, 1), (1, 100/255, 100/255), (100/255, 1, 100/255)]
        labels = ["1. Accion directa", "2. Energia mixta", "3. Intuicion"]
        for i, (pf, c, lb) in enumerate(zip(p_fracs, cols, labels)):
            appear = 0.25 + i * 0.20
            a = max(0.0, min(1.0, (prog - appear) / 0.15))
            if a <= 0:
                continue
            idx = int(len(vida) * pf)
            px, py = vida[idx]
            draw_pulsing_point(ctx, px, py, c, phase=(prog * 3) % 1.0)
            _set_font(ctx, 24, True)
            ext = ctx.text_extents(str(i + 1))
            ctx.set_source_rgb(0, 0, 0)
            ctx.move_to(px - ext.width/2, py + ext.height/2); ctx.show_text(str(i + 1))
            ly_ = box[1] + box[3] + 60 + i * 0  # placeholder
            _label(ctx, box[0] + box[2] + 40, box[1] + 20 + i * 46,
                   px + 18, py, lb, 15, alpha=a)
        # conectores punteados entre puntos
        if prog > 0.6:
            ctx.set_source_rgba(1, 1, 1, .5); ctx.set_line_width(2); ctx.set_dash([6, 3])
            for i in range(2):
                p1 = vida[int(len(vida) * p_fracs[i])]
                p2 = vida[int(len(vida) * p_fracs[i+1])]
                ctx.move_to(*p1); ctx.line_to(*p2); ctx.stroke()
            ctx.set_dash([])

    elif sid == 3:
        for i, box in enumerate(boxes):
            lines, montes = hand.anchors(box)
            # curva amplia (izq): control hacia afuera; estrecha (der): hacia adentro
            frac = max(0.0, min(1.0, (prog - 0.10) / 0.45))
            # deformar la linea de la vida
            cps = [list(p) for p in PALM["vida"]]
            if i == 0:
                cps[1][0] -= 0.10; cps[2][0] -= 0.09
                cps[1][1] += 0.03; cps[2][1] += 0.02
            else:
                cps[1][0] += 0.10; cps[2][0] += 0.06
            x, y, w_, h_ = box
            mir = (lambda p: (1 - p[0], p[1])) if not hand.thumb_right else (lambda p: p)
            pts = bez3(*[mir(tuple(c)) for c in cps])
            pts = [(x + px * w_, y + py * h_) for px, py in pts]
            draw_partial(ctx, pts, frac, LCOL["vida"], lw=6, dash=DASH["vida"], glow=True)
            ttl = "CURVA AMPLIA" if i == 0 else "ARCO ESTRECHO"
            _set_font(ctx, 22, True)
            ext = ctx.text_extents(ttl)
            ctx.set_source_rgba(1, 1, 1, title_a)
            ctx.move_to(x + w_/2 - ext.width/2, y - 18); ctx.show_text(ttl)
            if frac >= 1.0:
                _set_font(ctx, 16)
                sub = "Apertura y expansion" if i == 0 else "Energia concentrada"
                ext = ctx.text_extents(sub)
                ctx.set_source_rgba(.71, .63, .86, min(1.0, (prog - 0.6) / 0.2))
                ctx.move_to(x + w_/2 - ext.width/2, y + h_ + 34); ctx.show_text(sub)
        _set_font(ctx, 22, True)
        ext = ctx.text_extents("vs")
        ctx.set_source_rgb(.47, .47, .63)
        ctx.move_to(W/2 - ext.width/2, int(H * 0.55)); ctx.show_text("vs")

    elif sid == 4:
        box = boxes[0]
        lines, montes = hand.anchors(box)
        vida = lines["vida"]
        third = len(vida) // 3
        # tres estilos de intensidad sobre la misma linea
        f_total = max(0.0, min(1.0, prog / 0.35))
        draw_partial(ctx, vida[:third], f_total, LCOL["vida"], lw=9, glow=True)
        if prog > 0.35:
            f2 = min(1.0, (prog - 0.35) / 0.25)
            draw_partial(ctx, vida[third:2*third], f2, (200/255, 50/255, 80/255), lw=5,
                         dash=[8, 4])
        if prog > 0.60:
            f3 = min(1.0, (prog - 0.60) / 0.25)
            seg = vida[2*third:]
            n = max(2, int(len(seg) * f3))
            for i in range(0, n - 1, 2):
                ctx.set_source_rgb(.78, .59, .63); ctx.set_line_width(2)
                ctx.move_to(*seg[i]); ctx.line_to(*seg[min(i+1, n-1)]); ctx.stroke()
        la = max(0.0, min(1.0, (prog - 0.5) / 0.25))
        if la > 0:
            _label(ctx, box[0] + box[2] + 40, box[1] + 30,
                   *vida[third//2], "PROFUNDA", 15, (1, .39, .51), alpha=la)
            _label(ctx, box[0] + box[2] + 40, box[1] + 90,
                   *vida[third + third//2], "MEDIA", 15, (.78, .71, .63), alpha=la)
            _label(ctx, box[0] + box[2] + 40, box[1] + 150,
                   *vida[2*third + third//2], "SUAVE", 15, (.63, .55, .51), alpha=la)

    draw_title(ctx, W, H, cfg, alpha=title_a)
    draw_footer(ctx, W, H, sid, tot)

    # paneles de conceptos investigados (fade-in en la segunda mitad)
    if concept_infos:
        panel_a = max(0.0, min(1.0, (prog - 0.45) / 0.25))
        slots = [(0.685, 0.16, 0.27, 0.34), (0.685, 0.56, 0.27, 0.34)]
        for (photo_path, caption), slot in zip(concept_infos, slots):
            paste_concept_panel(base, photo_path, caption, panel_a, slot)

    # volcar cairo de vuelta a PIL
    final = Image.frombuffer("RGBA", (W, H), surf.get_data(), "raw", "BGRA", 0, 1)
    return final.convert("RGB")


def reversed_point(p):
    return (int(p[0]), int(p[1]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--storyboard", default=str(SCRIPT_DIR/"data"/"jobs"/"default"/"storyboard.json"))
    p.add_argument("--research", default=None, help="research.json (opcional)")
    p.add_argument("--output-dir", default=str(SCRIPT_DIR/"data"/"images"))
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--frames", type=int, default=7, help="keyframes por escena")
    a = p.parse_args()

    sb = json.loads(Path(a.storyboard).read_text(encoding="utf-8"))
    jid = Path(a.storyboard).parent.name
    research = {}
    if a.research and Path(a.research).exists():
        research = json.loads(Path(a.research).read_text(encoding="utf-8"))

    hand = HandPhoto(HAND_PATH)

    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    tot = len(sb["scenes"])
    meta = {"scenes": []}

    for sc in sb["scenes"]:
        sid = sc["id"]
        cfg = SCFG.get(sid, SCFG[1])
        scene_dir = out / f"scene_{sid:03d}"
        scene_dir.mkdir(parents=True, exist_ok=True)
        concept_infos = []
        for key in research.get("scenes", {}).get(str(sid), []):
            info = research.get("concepts", {}).get(key)
            if info and Path(info["file"]).exists():
                concept_infos.append((info["file"], info.get("label", key)))
        frames = []
        for ki in range(a.frames):
            fp = scene_dir / f"f_{ki:03d}.png"
            im = render_frame(sc, hand, concept_infos, ki, a.frames, a.width, a.height, sid, tot, cfg)
            im.save(fp, "PNG", optimize=False)
            frames.append(str(fp.name))
            print(f"  escena {sid} frame {ki+1}/{a.frames}")
        meta["scenes"].append({
            "scene_id": sid, "frames": frames, "dir": str(scene_dir),
            "concepts": [c[1] for c in concept_infos],
            "model": "hybrid-v6", "width": a.width, "height": a.height,
            "created_at": datetime.now().isoformat(),
        })
        print(f"Escena {sid}: {a.frames} keyframes, conceptos {[c[1] for c in concept_infos]}")

    (SCRIPT_DIR/"data"/"jobs"/jid/"images.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"scenes": tot, "keyframes_per_scene": a.frames, "dir": str(out)}))


if __name__ == "__main__":
    main()
