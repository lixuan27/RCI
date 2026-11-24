"""Render the RCI explainer videos in a hand-drawn whiteboard style (Pillow + ffmpeg).

Usage: python3 render.py overview|ladder|chain [--preview SECONDS]
Every number shown comes from the paper (Tables 2, 3, 6, 7, Figures 5b, 10, 11).
"""
import math, random, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

W, H, SS, FPS = 1280, 720, 3, 30
OW, OH = 1920, 1080
HAND = "/System/Library/Fonts/Supplemental/ChalkboardSE.ttc"
_fc = {}
def hand(sz, bold=False, light=False, heavy=False):
    # ChalkboardSE.ttc faces: 0 Light, 1 Regular, 2 Bold
    idx = 2 if heavy else (1 if bold else 0)
    k = (sz, idx)
    if k not in _fc:
        try: _fc[k] = ImageFont.truetype(HAND, int(sz * SS), index=idx)
        except OSError: _fc[k] = ImageFont.truetype(HAND, int(sz * SS), index=0)
    return _fc[k]

PAPER = (251, 250, 247); GRID = (233, 236, 236)
INK = (34, 34, 38); GREY = (112, 112, 118); LIGHT = (190, 192, 196)
BLUE = (47, 91, 211); BLUEF = (216, 228, 251); RED = (214, 64, 52); YEL = (246, 226, 150); YELD = (196, 150, 40)
GREEN = (46, 140, 87); GREENF = (214, 238, 222); PURP = (122, 92, 160); PURPF = (232, 224, 244); SLATE_C = (90, 120, 150)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def seg(t, a, b): return ease((t - a) / (b - a)) if b > a else float(t >= a)
def lerp(a, b, u): return a + (b - a) * u
def mixc(c1, c2, u): return tuple(int(lerp(a, b, u)) for a, b in zip(c1, c2))
def fade(col, a): return mixc(PAPER, col, clamp(a))

_bg = None
def background():
    global _bg
    if _bg is None:
        _bg = Image.new("RGB", (W * SS, H * SS), PAPER); d = ImageDraw.Draw(_bg)
        for x in range(0, W, 40): d.line([(x * SS, 0), (x * SS, H * SS)], fill=GRID, width=SS)
        for y in range(0, H, 40): d.line([(0, y * SS), (W * SS, y * SS)], fill=GRID, width=SS)
    return _bg.copy()

def rng(*key):
    return random.Random(hash(tuple(round(k, 1) if isinstance(k, float) else k for k in key)) & 0xffffffff)

class F:
    def __init__(self):
        self.im = background(); self.d = ImageDraw.Draw(self.im)
    def P(self, x, y): return (x * SS, y * SS)
    def text(self, x, y, s, f, col, a=1.0, anchor="la"):
        if a <= 0.01: return
        if "_" not in s:
            self.d.text(self.P(x, y), s, font=f, fill=fade(col, a), anchor=anchor); return
        parts = re.split(r"_([A-Za-z0-9])", s)
        sub = ImageFont.truetype(f.path, int(f.size * 0.66), index=f.index if hasattr(f, "index") else 0)
        widths = [(sub if i % 2 else f).getlength(p) for i, p in enumerate(parts)]
        tot = sum(widths); cx = x * SS - (tot / 2 if anchor[0] == "m" else tot if anchor[0] == "r" else 0)
        for i, p in enumerate(parts):
            if p:
                self.d.text((cx, y * SS + (f.size * 0.3 if i % 2 else 0)), p, font=sub if i % 2 else f, fill=fade(col, a), anchor="l" + anchor[1])
            cx += widths[i]
    def sline(self, x0, y0, x1, y1, col, a=1.0, w=2.5, key=0, passes=2, dash=None):
        """A sketched line: two slightly different strokes."""
        if a <= 0.01: return
        r = rng("l", x0, y0, x1, y1, key)
        for p in range(passes):
            j = lambda: r.uniform(-1.2, 1.2)
            pts = [(x0 + j(), y0 + j()), ((x0 + x1) / 2 + j() * 1.5, (y0 + y1) / 2 + j() * 1.5), (x1 + j(), y1 + j())]
            ww = w if p == 0 else max(1, w * 0.45); cc = fade(col, a if p == 0 else a * 0.45)
            if dash:
                L = math.hypot(x1 - x0, y1 - y0); n = int(L / (dash * 2)) + 1
                for i in range(n):
                    u0, u1 = i * 2 * dash / L, min(1, (i * 2 + 1) * dash / L)
                    if u0 >= 1: break
                    self.d.line([self.P(lerp(x0, x1, u0), lerp(y0, y1, u0)), self.P(lerp(x0, x1, u1), lerp(y0, y1, u1))], fill=cc, width=int(ww * SS))
                break
            self.d.line([self.P(*q) for q in pts], fill=cc, width=int(ww * SS), joint="curve")
    def srect(self, x0, y0, x1, y1, stroke, fill=None, a=1.0, w=2.5, key=0):
        if a <= 0.01: return
        if fill: self.d.rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=fade(fill, a))
        for (p, q) in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
            self.sline(p[0], p[1], q[0], q[1], stroke, a, w, key)
    def scircle(self, x, y, rr, stroke, fill=None, a=1.0, w=3, key=0):
        if a <= 0.01: return
        if fill: self.d.ellipse([(x - rr) * SS, (y - rr) * SS, (x + rr) * SS, (y + rr) * SS], fill=fade(fill, a))
        r = rng("c", x, y, rr, key)
        for p in range(2):
            ph, amp, off = r.uniform(0, 6.3), rr * 0.035, r.uniform(-1.5, 1.5)
            pts = [(x + off + (rr + amp * math.sin(3 * th + ph)) * math.cos(th), y + off * 0.5 + (rr + amp * math.sin(3 * th + ph)) * math.sin(th))
                   for th in [i / 48 * 2 * math.pi + 0.15 * p for i in range(51)]]
            self.d.line([self.P(*q) for q in pts], fill=fade(stroke, a if p == 0 else a * 0.4), width=int((w if p == 0 else 1.5) * SS), joint="curve")
    def dot(self, x, y, rr, col, a=1.0):
        if a > 0.01: self.d.ellipse([(x - rr) * SS, (y - rr) * SS, (x + rr) * SS, (y + rr) * SS], fill=fade(col, a))
    def arc(self, x, y, rr, a0, a1, col, a=1.0, w=3):
        if a > 0.01: self.d.arc([(x - rr) * SS, (y - rr) * SS, (x + rr) * SS, (y + rr) * SS], a0, a1, fill=fade(col, a), width=int(w * SS))
    def arrow(self, x0, y0, x1, y1, col, a=1.0, w=2.5, head=12, key=0):
        self.sline(x0, y0, x1, y1, col, a, w, key)
        ang = math.atan2(y1 - y0, x1 - x0)
        for s in (-0.5, 0.5):
            self.sline(x1, y1, x1 - head * math.cos(ang + s), y1 - head * math.sin(ang + s), col, a, w, key + 7, passes=1)
    def check(self, x, y, col=GREEN, a=1.0, s=1.0):
        self.sline(x - 14 * s, y, x - 4 * s, y + 12 * s, col, a, 5, passes=1); self.sline(x - 4 * s, y + 12 * s, x + 18 * s, y - 16 * s, col, a, 5, passes=1)
    def cross(self, x, y, col=RED, a=1.0, s=1.0):
        self.sline(x - 14 * s, y - 14 * s, x + 14 * s, y + 14 * s, col, a, 5, passes=1); self.sline(x - 14 * s, y + 14 * s, x + 14 * s, y - 14 * s, col, a, 5, passes=1)
    def out(self): return self.im.resize((OW, OH), Image.LANCZOS)

def smiley(f, x, y, a=1.0, s=1.0, mood="happy", key=0, fill=BLUEF, stroke=BLUE):
    rr = 38 * s
    f.scircle(x, y, rr, stroke, fill, a, 3 * s, key)
    f.dot(x - 11 * s, y - 6 * s, 3.6 * s, INK, a); f.dot(x + 11 * s, y - 6 * s, 3.6 * s, INK, a)
    if mood == "happy": f.arc(x, y + 2 * s, 13 * s, 30, 150, INK, a, 2.6 * s)
    elif mood == "sad": f.arc(x, y + 22 * s, 12 * s, 215, 325, INK, a, 2.6 * s)
    else: f.sline(x - 9 * s, y + 13 * s, x + 9 * s, y + 13 * s, INK, a, 2.4 * s, passes=1)
def sticky(f, x, y, label, a=1.0, s=1.0, key=0):
    w, h = 34 * s, 28 * s
    f.srect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, INK, YEL, a, 1.8, key)
    f.text(x, y + 1, label, hand(17 * s, True), INK, a, "mm")
def bubble(f, x, y, a=1.0, key=0):
    f.srect(x - 16, y - 11, x + 16, y + 9, GREY, (255, 255, 255), a, 1.6, key)
    for k in (-7, 0, 7): f.dot(x + k, y - 1, 2, GREY, a)
def coin(f, x, y, label="+1", a=1.0, key=0):
    f.scircle(x, y, 18, YELD, YEL, a, 2.5, key); f.text(x, y + 1, label, hand(15, True), INK, a, "mm")
def heading(f, t, a, b, s, x=70, y=58):
    al = seg(t, a, a + 0.6) * (1 - seg(t, b - 0.6, b))
    f.text(x, y, s, hand(38, True), INK, al, "ls")
    w = hand(38, True).getlength(s) / SS
    f.sline(x, y + 14, x + w * seg(t, a + 0.2, a + 1.0), y + 14, BLUE, al, 4, passes=1)
def say(f, t, a, b, s, y=640, size=30, col=INK, bold=True):
    al = seg(t, a, a + 0.6) * (1 - seg(t, b - 0.6, b))
    f.text(W / 2, y, s, hand(size, bold), col, al, "mm")

def stairs(f, x0, yb, a, lit=0, w=200, hs=(70, 130, 190), labels=True, key=0):
    names = ["beats one agent", "beats the majority vote", "beats pass@n"]
    fills = [(226, 232, 240), (198, 214, 236), (190, 226, 204)]
    for i in range(3):
        x = x0 + i * w; on = lit > i
        f.srect(x, yb - hs[i], x + w, yb, INK, fills[i] if on else (246, 246, 244), a, 2.5, key + i)
        f.text(x + 16, yb - hs[i] + 34, str(i + 1), hand(34, True), BLUE if on else LIGHT, a, "ls")
        if labels: f.text(x + w / 2, yb + 28, names[i], hand(19, True), INK if on else LIGHT, a, "mm")

# ------------------------------------------------------------------ overview (~116 s)
def panel(f, x0, y0, x1, y1, title, a, key=0):
    f.srect(x0, y0, x1, y1, GREY, (255, 255, 255), a, 1.8, key)
    f.text(x0 + 12, y0 + 22, title, hand(19), GREY, a, "lm")
def takeaway(f, t, a, b, lines, y=600):
    for k, (s, col) in enumerate(lines):
        al = seg(t, a + k * 0.5, a + k * 0.5 + 0.6) * (1 - seg(t, b - 0.6, b))
        f.text(W / 2, y + k * 34, s, hand(24, True), col, al, "mm")

PRIOR = {"debate": [-0.005, 0.008, 0.022, -0.055, -0.178, -0.163, -0.016, -0.016, -0.173, -0.057, -0.045],
         "DeLM": [0.022, 0.015, 0.022, -0.002, -0.243, -0.066, -0.506, -0.235, -0.304],
         "AOrchestra": [0.021, -0.075, -0.112, -0.360]}
REVIEWER27 = [0.050, 0.131, 0.037, 0.044]

def overview(t):
    f = F()
    if t < 7.5:                                    # 1 title
        a = seg(t, 0.2, 1.0) * (1 - seg(t, 6.8, 7.5))
        f.text(W / 2, 118, "Is a group of agents smarter than its members?", hand(50, heavy=True), INK, a, "mm")
        f.text(W / 2, 210, "?", hand(62, heavy=True), RED, a * seg(t, 0.8, 1.4), "mm")
        for i in range(5): smiley(f, 400 + i * 120, 330, a * seg(t, 1 + i * 0.15, 1.6 + i * 0.15), 0.85, key=i)
        f.text(W / 2, 400, "five copies of one model", hand(22), GREY, a, "mm")
        f.text(W / 2, 520, "Recursive Collective Intelligence", hand(30, True), BLUE, a * seg(t, 2.2, 3.0), "mm")
    elif t < 21.5:                                 # 2 what counts
        u = t - 7.5; a = seg(u, 0.2, 0.9) * (1 - seg(u, 13.3, 14))
        heading(f, u, 0, 14, "What counts as collective intelligence")
        f.text(320, 120, "Independent agents", hand(24, True), INK, a, "mm")
        f.sline(640, 110, 640, 420, LIGHT, a, 2, dash=8)
        f.text(960, 120, "Interacting agents", hand(24, True), INK, a * seg(u, 2, 2.8), "mm")
        xs = [200, 280, 360, 440]
        for i, x in enumerate(xs): smiley(f, x, 190, a, 0.62, "neutral", key=20 + i)
        v = seg(u, 0.8, 2)
        for x in xs: f.sline(x, 215, 320, 330, GREY, a * v, 1.6, key=int(x))
        f.srect(285, 330, 355, 368, INK, (255, 255, 255), a * v, 2, 25); f.text(320, 349, "vote", hand(19, True), INK, a * v, "mm")
        b = seg(u, 2, 3)
        pts = [(860, 170), (1060, 170), (860, 320), (1060, 320)]
        f.srect(915, 215, 1005, 275, INK, (255, 255, 255), a * b, 2, 26); f.text(960, 200, "blackboard", hand(15), GREY, a * b, "mm")
        for k in range(3): f.srect(928 + k * 24, 236, 946 + k * 24, 253, INK, YEL, a * b, 1.4, 27 + k)
        for i, p in enumerate(pts):
            smiley(f, *p, a * b, 0.62, key=30 + i); f.sline(p[0], p[1], 960, 245, BLUE, a * b, 1.6, key=31 + i, dash=6)
        c = seg(u, 5, 6.5)
        f.srect(240, 470, 240 + 40, 490, INK, (198, 214, 236), a * c, 2, 40); f.text(300, 480, "one agent: 1x tokens", hand(20), INK, a * c, "lm")
        f.srect(760, 470, 760 + 300, 490, INK, PURPF, a * c, 2, 41); f.text(910, 512, "interacting group: 8.8x tokens", hand(20), INK, a * c, "mm")
        takeaway(f, u, 7.5, 14, [("Interaction spends more tokens.", INK),
                                 ("We compare groups with independent agents at equal budget.", BLUE)], y=580)
    elif t < 37.5:                                 # 3 ladder
        u = t - 21.5; a = seg(u, 0.2, 0.9) * (1 - seg(u, 15.3, 16))
        heading(f, u, 0, 16, "The equal-budget ladder")
        f.text(W / 2, 128, "token budget: n_B = k / c_1 independent agents", hand(26, True), BLUE, a * seg(u, 0.5, 1.3), "mm")
        lit = (u > 3) + (u > 5.5) + (u > 8)
        stairs(f, 310, 430, a, lit, w=220, key=60)
        f.sline(290, 430 - 190 - 16, 990, 430 - 190 - 16, RED, a * seg(u, 9.5, 10.3), 2.5, dash=9)
        f.text(1005, 430 - 190 - 16, "pass@n", hand(22, True), RED, a * seg(u, 9.5, 10.3), "lm")
        f.text(W / 2, 500, "Votes and judges select among existing answers.", hand(21), GREY, a * seg(u, 10, 11), "mm")
        takeaway(f, u, 11, 16, [("Level 3 requires answers that the group creates together.", GREEN)], y=580)
    elif t < 51.5:                                 # 4 shared information
        u = t - 37.5; a = seg(u, 0.2, 0.9) * (1 - seg(u, 13.3, 14))
        heading(f, u, 0, 14, "Shared information")
        panel(f, 70, 110, 470, 470, "every agent sees the full task", a, 70)
        for i, (x, y) in enumerate([(170, 220), (370, 220), (170, 380), (370, 380)]):
            smiley(f, x, y, a, 0.6, "neutral", key=71 + i)
            f.srect(x - 16, y + 32, x + 16, y + 54, INK, YEL, a, 1.4, 75 + i); f.text(x, y + 43, "ABCD", hand(10, True), INK, a, "mm")
        for i in range(4):
            ph = (u * 0.5 + i * 0.25) % 1
            bubble(f, lerp(170, 370, ph), lerp(220, 380, (ph + i * 0.3) % 1), a * seg(u, 1, 2), key=80 + i)
        f.text(270, 455, "messages repeat known information", hand(16), GREY, a * seg(u, 2, 3), "mm")
        panel(f, 520, 110, 1210, 470, "gain over the equal-budget vote (Qwen3.5-9B)", a, 90)
        X = lambda v: lerp(600, 1180, (v + 0.55) / 0.75)
        f.sline(X(0), 140, X(0), 450, INK, a, 2, dash=7); f.text(X(0), 462, "vote", hand(17, True), INK, a, "mm")
        rows = [("debate", PRIOR["debate"], PURP), ("DeLM", PRIOR["DeLM"], SLATE_C), ("AOrchestra", PRIOR["AOrchestra"], GREY), ("27B reviewer", REVIEWER27, GREEN)]
        for k, (nm, vals, col) in enumerate(rows):
            y = 185 + k * 72; r = seg(u, 2 + k * 1.6, 3.2 + k * 1.6)
            f.text(610, y, nm, hand(19, True), col, a * r, "lm")
            for j, v in enumerate(vals):
                f.scircle(lerp(X(0), X(v), r), y + 22, 6, col, (255, 255, 255), a * r, 2, key=100 + k * 20 + j)
        takeaway(f, u, 8.5, 14, [("Prior multi-agent methods stay at the equal-budget vote.", RED),
                                 ("A stronger 27B reviewer beats the vote.", GREEN)], y=560)
    elif t < 67.5:                                 # 5 split facts
        u = t - 51.5; a = seg(u, 0.2, 0.9) * (1 - seg(u, 15.3, 16))
        heading(f, u, 0, 16, "Split facts")
        f.text(70, 112, "HiddenBench: each Qwen3.8-27B agent holds part of the facts", hand(20), GREY, a, "la")
        for side, (x0, title, col) in enumerate([(70, "Debate", PURP), (660, "Fact forwarding", GREEN)]):
            pa = a * seg(u, 0.6 + side * 3.5, 1.4 + side * 3.5)
            panel(f, x0, 140, x0 + 550, 470, title, pa, 140 + side)
            pts = [(x0 + 150, 230), (x0 + 400, 230), (x0 + 150, 380), (x0 + 400, 380)]
            done = side == 1 and u > 8
            for i, p in enumerate(pts):
                smiley(f, *p, pa, 0.6, "happy" if done else "neutral", key=150 + side * 10 + i)
                hold = [i] + ([j for j in range(4) if j != i] if done else [])
                for k, j in enumerate(hold): sticky(f, p[0] - 50 + k * 33, p[1] + 50, "ABCD"[j], pa, 0.75, key=160 + side * 20 + i * 4 + k)
            for i in range(4):
                for j in range(4):
                    if i == j: continue
                    if side == 0:
                        ph = (u * 0.45 + (i * 4 + j) * 0.07) % 1
                        if (i + j) % 2: bubble(f, lerp(pts[i][0], pts[j][0], ph), lerp(pts[i][1], pts[j][1], ph), pa, key=i * 4 + j)
                    else:
                        ph = clamp((u - 5 - i * 0.35) / 2.2)
                        if 0 < ph < 1: sticky(f, lerp(pts[i][0], pts[j][0], ph), lerp(pts[i][1], pts[j][1], ph), "ABCD"[i], pa, 0.6, key=i)
        f.text(345, 500, "level 2: 0.688 vs pass@n 0.703", hand(22, True), PURP, a * seg(u, 3, 3.8), "mm")
        f.text(935, 500, "level 3: 0.959 vs pass@n 0.649", hand(22, True), GREEN, a * seg(u, 9, 9.8), "mm")
        takeaway(f, u, 10.5, 16, [("Fact forwarding exceeds pass@n by 31 points.", INK)], y=580)
    elif t < 81.5:                                 # 6 organization
        u = t - 67.5; a = seg(u, 0.2, 0.9) * (1 - seg(u, 13.3, 14))
        heading(f, u, 0, 14, "Emergent organization")
        panel(f, 70, 110, 620, 470, "each agent can give its reading budget away", a, 200)
        hub = (345, 300); oth = [(170, 190), (170, 410), (520, 190)]
        smiley(f, *hub, a, 0.95, "happy" if u > 6.5 else "neutral", key=210)
        for i, p in enumerate(oth): smiley(f, *p, a, 0.62, key=211 + i)
        for i, p in enumerate(oth):
            ph = clamp((u - 1.5 - i * 0.5) / 2.0)
            if 0 < ph < 1: coin(f, lerp(p[0], hub[0], ph), lerp(p[1], hub[1], ph), "+1", a, key=220 + i)
            ph2 = clamp((u - 4.5 - i * 0.4) / 1.8)
            if 0 < ph2 < 1: sticky(f, lerp(p[0], hub[0], ph2), lerp(p[1], hub[1], ph2), "BCD"[i], a, 0.7, key=230 + i)
        f.text(hub[0], hub[1] + 60, "a hub reads every fact", hand(19, True), RED, a * seg(u, 6.5, 7.3), "mm")
        f.text(920, 170, "+18 points", hand(50, heavy=True), GREEN, a * seg(u, 7, 7.8), "mm")
        f.text(920, 212, "accuracy gain from budget transfers", hand(20), GREY, a * seg(u, 7, 7.8), "mm")
        c = seg(u, 8.5, 10)
        f.srect(740, 255, 740 + 360 * 0.67 * c, 283, INK, (246, 206, 200), a * c, 2, 240)
        f.srect(740 + 360 * 0.67 * c, 255, 740 + 360 * c, 283, INK, GREENF, a * c, 2, 241)
        f.text(860, 302, "coordination", hand(18, True), RED, a * c, "mm"); f.text(1040, 302, "work", hand(18, True), GREEN, a * c, "mm")
        n = seg(u, 10, 11)
        f.srect(700, 345, 752, 415, INK, (255, 255, 255), a * n, 2, 242)
        for k in range(4): f.sline(710, 360 + k * 13, 742, 360 + k * 13, LIGHT, a * n, 2, key=243 + k, passes=1)
        f.text(770, 362, "A self-written prompt describes", hand(19, True), INK, a * n, "la")
        f.text(770, 390, "the same hub and reaches level 3", hand(19, True), INK, a * n, "la")
        f.text(770, 418, "at less than half the budget", hand(19, True), INK, a * n, "la")
        takeaway(f, u, 11, 14, [("Coordination takes about two thirds of the tokens.", INK)], y=560)
    elif t < 97.5:                                 # 7 improving without labels
        u = t - 81.5; a = seg(u, 0.2, 0.9) * (1 - seg(u, 15.3, 16))
        heading(f, u, 0, 16, "Label-free training")
        def mini_group(x, y, aa, key):
            for k, (dx, dy) in enumerate([(-16, 8), (0, -10), (16, 8)]): smiley(f, x + dx, y + dy, aa, 0.36, key=key + k)
        mini_group(140, 175, a, 300); f.text(140, 222, "generation g", hand(16), GREY, a, "mm")
        f.arrow(185, 175, 290, 175, INK, a, 2, key=303); f.text(237, 155, "plays fresh tasks", hand(14), GREY, a, "mm")
        f.srect(300, 140, 360, 210, INK, (255, 255, 255), a, 2, 304); f.check(330, 175, GREEN, a, 0.8)
        f.text(330, 228, "automatic check", hand(14), GREY, a, "mm")
        f.arrow(370, 175, 480, 175, INK, a * seg(u, 1, 2), 2, key=305); f.text(425, 155, "train candidates", hand(14), GREY, a * seg(u, 1, 2), "mm")
        f.srect(490, 140, 600, 210, INK, YEL, a * seg(u, 2, 3), 2, 306); f.text(545, 175, "confirm on", hand(14, True), INK, a * seg(u, 2, 3), "mm"); f.text(545, 193, "fresh tasks?", hand(14, True), INK, a * seg(u, 2, 3), "mm")
        f.arrow(610, 175, 720, 175, GREEN, a * seg(u, 3, 4), 2, key=307); f.text(665, 155, "release", hand(14, True), GREEN, a * seg(u, 3, 4), "mm")
        mini_group(770, 175, a * seg(u, 3, 4), 308); f.text(770, 222, "generation g+1", hand(16), GREY, a * seg(u, 3, 4), "mm")
        g = seg(u, 4, 5); f.sline(140, 128, 770, 128, BLUE, a * g, 2, key=311, dash=6); f.text(455, 112, "generation after generation", hand(16, True), BLUE, a * g, "mm")
        rows = [("Single-agent self-training", [0.396, 0.563, 0.658], LIGHT, (226, 228, 230)), ("Collective training (ours)", [0.703, 0.755, 0.836], GREEN, GREENF)]
        for k, (nm, vals, col, fillc) in enumerate(rows):
            y0 = 275 + k * 150; r = seg(u, 5 + k * 2.5, 6 + k * 2.5)
            f.text(80, y0, nm, hand(20, True), INK, a * r, "la")
            for j, v in enumerate(vals):
                x = 140 + j * 210; q = seg(u, 5.5 + k * 2.5 + j * 0.5, 6.3 + k * 2.5 + j * 0.5)
                mini_group(x, y0 + 60, a * q, 320 + k * 10 + j)
                f.srect(x + 42, y0 + 115 - 100 * v * q, x + 70, y0 + 115, INK, fillc, a * q, 1.8, 340 + k * 10 + j)
                f.text(x + 56, y0 + 132, f"{v:.3f}", hand(16, True), INK, a * q, "mm")
                f.text(x, y0 + 100, f"G{j + 1}", hand(15), GREY, a * q, "mm")
        f.text(820, 360, "HiddenBench with equal training caps", hand(18), GREY, a * seg(u, 6, 7), "la")
        takeaway(f, u, 11, 16, [("Collective training stays far above single-agent self-training.", GREEN)], y=640)
    elif t < 107.5:                                # 8 three benchmarks
        u = t - 97.5; a = seg(u, 0.2, 0.9) * (1 - seg(u, 9.3, 10))
        heading(f, u, 0, 10, "Recursion on three benchmarks")
        charts = [("PlanBench", [0.613, 0.857, 0.937, 0.940, 0.950], 0, 1, BLUE, "0.613 to 0.950 in 4 generations"),
                  ("HiddenBench", [0.509, 0.713, 0.791, 0.811, 0.845, 0.886], 0.4, 1, PURP, "0.509 to 0.886 in 5 generations"),
                  ("Hanabi (score / 25)", [0, 0.678, 2.953, 4.110, 4.420, 4.523, 4.482], 0, 5, RED, "0 to 4.5 in 6 generations")]
        for k, (nm, v, lo, hi, col, lab) in enumerate(charts):
            x0, y0, cw, ch = 100 + k * 390, 170, 300, 250
            f.text(x0, y0 - 24, nm, hand(22, True), INK, a, "la")
            f.sline(x0, y0 + ch, x0 + cw, y0 + ch, INK, a, 2, key=400 + k); f.sline(x0, y0, x0, y0 + ch, INK, a, 2, key=410 + k)
            gg = seg(u, 0.8 + k * 0.6, 5 + k * 0.6) * (len(v) - 1)
            P = [(x0 + i * cw / (len(v) - 1), y0 + ch - (v[i] - lo) / (hi - lo) * ch * 0.92) for i in range(len(v))]
            for i in range(len(v) - 1):
                if gg > i:
                    q = clamp(gg - i); f.sline(P[i][0], P[i][1], lerp(P[i][0], P[i + 1][0], q), lerp(P[i][1], P[i + 1][1], q), col, a, 3.5, key=420 + k * 10 + i, passes=1)
            for i, p in enumerate(P):
                if gg >= i: f.dot(p[0], p[1], 5, col, a)
            f.text(x0 + cw / 2, y0 + ch + 32, lab, hand(19, True), col, a * seg(u, 5 + k * 0.6, 5.8 + k * 0.6), "mm")
        takeaway(f, u, 6.5, 10, [("Every released generation beats its predecessor on unseen tasks.", INK)], y=560)
    else:                                          # 9 summary
        u = t - 107.5; a = seg(u, 0.2, 0.9) * (1 - seg(u, 8.4, 9))
        heading(f, u, 0, 9, "Summary")
        items = [("Grade groups against independent agents at equal budget.", "scale"),
                 ("Fact forwarding lifts groups above pass@n.", "fact"),
                 ("Identical agents form hubs at a coordination cost.", "coin"),
                 ("Groups improve over four to six label-free generations.", "loop")]
        for k, (s, icon) in enumerate(items):
            y = 150 + k * 78; r = a * seg(u, 0.5 + k * 0.8, 1.2 + k * 0.8)
            x = 150
            if icon == "scale":
                f.sline(x - 22, y, x + 22, y, INK, r, 2.5, key=500); f.sline(x, y - 16, x, y + 14, INK, r, 2.5, key=501)
                f.arc(x - 22, y + 2, 9, 0, 180, INK, r, 2); f.arc(x + 22, y + 2, 9, 0, 180, INK, r, 2)
            elif icon == "fact": sticky(f, x, y, "A", r, 1.0, key=502)
            elif icon == "coin": coin(f, x, y, "+1", r, key=503)
            else:
                f.arc(x, y, 16, 200, 520, BLUE, r, 2.5); f.sline(x + 13, y - 12, x + 20, y - 3, BLUE, r, 2.5, passes=1)
            f.text(x + 46, y, s, hand(23, True), INK, r, "lm")
        for i in range(5): smiley(f, 470 + i * 85, 520, a * seg(u, 4, 5), 0.6, "happy", key=520 + i)
        f.text(W / 2, 600, "lixuan27.github.io/RCI", hand(22), GREY, a * seg(u, 4.5, 5.5), "mm")
    return f.out()

# ------------------------------------------------------------------ ladder (~30 s)
PROTOS = [("Blackboard", -0.331, PURP), ("Debate (2 rounds)", -0.015, PURP), ("Blackboard + hint", 0.043, PURP), ("Debate (2 rounds) + hint", 0.079, PURP),
          ("Debate (3 rounds) + hint", 0.109, PURP), ("Facts-only blackboard", 0.137, GREEN), ("Shared context", 0.190, GREEN), ("Gated blackboard", 0.234, GREEN),
          ("Fact forwarding", 0.310, GREEN), ("Shared context + forwarding", 0.328, GREEN)]
def ladder_video(t):
    f = F(); a = seg(t, 0.2, 1.0) * (1 - seg(t, 29.2, 30))
    heading(f, t, 0, 30, "Where protocols land on the ladder")
    f.text(70, 108, "HiddenBench with four Qwen3.8-27B agents: margin over pass@n_B", hand(21, light=True), GREY, a, "la")
    x0, x1, y0, rh = 540, 1180, 165, 44
    X = lambda m: lerp(x0, x1, (m + 0.36) / 0.72)
    f.srect(X(0), y0 - 14, x1, y0 + rh * 10, GREEN, GREENF, a * 0.6, 1.5, key=1)
    f.sline(X(0), y0 - 24, X(0), y0 + rh * 10 + 8, RED, a, 2.5, dash=8)
    f.text(X(0), y0 + rh * 10 + 30, "pass@n_B", hand(20, True), RED, a, "mm")
    f.text(x1 - 10, y0 + 4, "level 3", hand(20, True), GREEN, a, "rm")
    for i, (nm, m, col) in enumerate(PROTOS):
        y = y0 + i * rh + 12; ap = seg(t, 2 + i * 2.2, 3 + i * 2.2)
        f.text(x0 - 22, y, nm, hand(21, True), col, a * ap, "rm")
        xm = lerp(X(0), X(m), ease(clamp((t - 2.3 - i * 2.2) / 1.2)))
        f.sline(X(0), y, xm, y, col, a * ap, 7, key=10 + i, passes=1)
        f.scircle(xm, y, 9, col, (255, 255, 255), a * ap, 2.5, key=20 + i)
        f.text(xm + 18 if m >= 0 else X(0) + 18, y, f"{m:+.3f}", hand(18, True), INK, a * seg(t, 3.4 + i * 2.2, 4 + i * 2.2), "lm")
    say(f, t, 24, 30, "Fact protocols rise above pass@n.", y=680, size=24, col=INK)
    return f.out()

# ------------------------------------------------------------------ chain (~36 s)
ROUNDS = [(1, 0.4913, 0.6946, 0.203, "G1"), (2, 0.7344, 0.7788, 0.044, "G2"), (3, 0.8069, 0.8075, 0.001, None), (4, 0.7800, 0.8238, 0.044, "G3"),
          (5, 0.7900, 0.8550, 0.065, "G4"), (6, 0.8250, 0.8263, 0.001, None), (7, 0.8237, 0.8700, 0.046, "G5"), (8, 0.9038, 0.9183, 0.015, None)]
def chain_video(t):
    f = F(); a = seg(t, 0.2, 1.0) * (1 - seg(t, 35.2, 36))
    heading(f, t, 0, 36, "Gated generation chain")
    f.text(70, 108, "HiddenBench: each candidate meets the current generation on fresh confirmation tasks", hand(21, light=True), GREY, a, "la")
    per = 3.6; r = int(clamp((t - 2) / per, 0, 7.999)); u = (t - 2) - r * per
    gen = sum(1 for k in range(8) if ROUNDS[k][4] and (k < r or (k == r and u > 2.4)))
    if t > 2:
        rnd, par, cand, d, rel = ROUNDS[r]
        f.text(250, 170, f"round {rnd}", hand(36, True), INK, a, "mm")
        base = 470; sc = lambda v: (v - 0.4) / 0.6 * 250
        g1, g2 = seg(u, 0.1, 0.9), seg(u, 0.6, 1.5)
        f.srect(150, base - sc(par) * g1, 230, base, INK, BLUEF, a, 2.2, key=500 + r)
        f.srect(270, base - sc(cand) * g2, 350, base, INK, YEL, a, 2.2, key=520 + r)
        f.text(190, base + 26, "current", hand(20, light=True), GREY, a, "mm"); f.text(310, base + 26, "candidate", hand(20, light=True), GREY, a, "mm")
        f.text(190, base - sc(par) * g1 - 20, f"{par:.3f}", hand(19, True), INK, a * g1, "mm"); f.text(310, base - sc(cand) * g2 - 20, f"{cand:.3f}", hand(19, True), INK, a * g2, "mm")
        dv = seg(u, 1.6, 2.2)
        f.text(250, 548, f"paired gain d = {d:+.3f}", hand(24, True), INK, a * dv, "mm")
        f.text(250, 580, "threshold 0.026", hand(20, light=True), GREY, a * dv, "mm")
        v = seg(u, 2.3, 2.8)
        if rel: f.check(120, 640, GREEN, a * v); f.text(150, 640, f"released as {rel}", hand(26, True), GREEN, a * v, "lm")
        else: f.cross(120, 640, RED, a * v, 0.8); f.text(150, 640, "flat round", hand(24, True), RED, a * v, "lm")
    gx0, gy = 560, 300
    vals = [0.509, 0.713, 0.791, 0.811, 0.845, 0.886]
    for k in range(6):
        x = gx0 + k * 118; on = k <= gen
        smiley(f, x, gy, a, 0.62, "happy" if on else "neutral", key=600 + k, fill=BLUEF if on else (243, 243, 241), stroke=BLUE if on else LIGHT)
        f.text(x, gy + 46, f"G{k}", hand(20, True), INK if on else LIGHT, a, "mm")
        if on: f.text(x, gy + 74, f"{vals[k]:.3f}", hand(18, light=True), GREY, a, "mm")
        if k < 5: f.arrow(x + 30, gy, x + 86, gy, BLUE if k < gen else LIGHT, a, 2.2, 10, key=610 + k)
    f.text(gx0 + 295, gy + 112, "group accuracy on the selection set", hand(19, light=True), GREY, a, "mm")
    f.text(gx0 + 295, 520, "Five releases in eight rounds.", hand(23, True), INK, a * seg(t, 31, 32), "mm")
    f.text(gx0 + 295, 556, "Fresh confirmation tasks guard every release.", hand(21, light=True), GREY, a * seg(t, 31.5, 32.5), "mm")
    return f.out()

SCENES = {"overview": (overview, 116.5), "ladder": (ladder_video, 30), "chain": (chain_video, 36)}
SCRATCH = "."

def render(name, out, preview=None):
    fn, dur = SCENES[name]
    if preview is not None:
        fn(preview).save(out); return
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21", "-preset", "medium", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n = int(dur * FPS)
    for i in range(n):
        p.stdin.write(fn(i / FPS).tobytes())
        if i % 300 == 0: print(name, i, "/", n, flush=True)
    p.stdin.close(); p.wait()
    fn(dur * 0.42).save(out.replace(".mp4", "_poster.jpg"), quality=88)
    print("done", out, flush=True)

if __name__ == "__main__":
    name = sys.argv[1]
    if len(sys.argv) > 3 and sys.argv[2] == "--preview":
        render(name, f"{SCRATCH}/{name}_{sys.argv[3]}.png", float(sys.argv[3]))
    else:
        render(name, f"{name}.mp4")
