"""Render the RCI explainer videos in a hand-drawn whiteboard style (Pillow + ffmpeg).

Usage: python3 render.py overview|ladder|chain [--preview SECONDS]
Every number shown comes from the paper (Tables 2, 3, 6, 7, Figures 5b, 10, 11).
"""
import math, random, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

W, H, SS, FPS = 1280, 720, 2, 30
HAND = "/System/Library/Fonts/Supplemental/ChalkboardSE.ttc"
_fc = {}
def hand(sz, bold=False, light=False):
    idx = 1 if bold else (2 if light else 0)
    k = (sz, idx)
    if k not in _fc:
        try: _fc[k] = ImageFont.truetype(HAND, int(sz * SS), index=idx)
        except OSError: _fc[k] = ImageFont.truetype(HAND, int(sz * SS), index=0)
    return _fc[k]

PAPER = (251, 250, 247); GRID = (233, 236, 236)
INK = (34, 34, 38); GREY = (112, 112, 118); LIGHT = (190, 192, 196)
BLUE = (47, 91, 211); BLUEF = (216, 228, 251); RED = (214, 64, 52); YEL = (246, 226, 150); YELD = (196, 150, 40)
GREEN = (46, 140, 87); GREENF = (214, 238, 222); PURP = (122, 92, 160); PURPF = (232, 224, 244)

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
    def out(self): return self.im.resize((W, H), Image.LANCZOS)

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
    f.text(x, y, s, hand(40, True), INK, al, "ls")
    w = hand(40, True).getlength(s) / SS
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

# ------------------------------------------------------------------ overview (~110 s)
def overview(t):
    f = F()
    if t < 8.5:                                   # S1
        a = seg(t, 0.2, 1.2) * (1 - seg(t, 7.6, 8.4))
        f.text(W / 2, 120, "Is a group of agents smarter than one?", hand(58, True), INK, a, "mm")
        f.text(W / 2, 222, "?", hand(70, True), RED, a * seg(t, 1, 1.6), "mm")
        for i in range(4): smiley(f, 400 + i * 160, 360, a * seg(t, 1.2 + i * 0.2, 1.8 + i * 0.2), 1.0, key=i)
        f.text(W / 2, 445, "four copies of one model", hand(24, light=True), GREY, a, "mm")
        f.text(W / 2, 560, "Recursive Collective Intelligence, told with a few circles", hand(34, True), BLUE, a * seg(t, 2.5, 3.3), "mm")
    elif t < 24.5:                                # S2
        u = t - 8; a = seg(u, 0.2, 1.0) * (1 - seg(u, 15.6, 16.4))
        heading(f, u, 0, 16.4, "A team spends more tokens")
        smiley(f, 190, 260, a, 1.0, key=11); f.text(190, 330, "one agent", hand(22, light=True), GREY, a, "mm")
        f.srect(150, 360, 230, 384, INK, (198, 214, 236), a, 2, 12); f.text(190, 412, "1x tokens", hand(20, True), INK, a, "mm")
        pts = [(470, 210), (600, 210), (470, 330), (600, 330)]
        for i, p in enumerate(pts): smiley(f, *p, a, 0.85, key=20 + i)
        g = seg(u, 1.5, 6)
        for i in range(4):
            for j in range(i + 1, 4):
                ph = (u * 0.55 + (i + j) * 0.17) % 1
                bubble(f, lerp(pts[i][0], pts[j][0], ph), lerp(pts[i][1], pts[j][1], ph), a * g, key=i * 4 + j)
        f.srect(430, 380, 430 + 220 * g, 404, INK, (232, 224, 244), a * g, 2, 13)
        f.text(535, 432, f"{lerp(1, 8.8, g):.1f}x tokens", hand(20, True), INK, a * g, "mm")
        say(f, u, 1.0, 7.6, "Most evaluations credit a team for beating one agent ...", y=640, size=28)
        b = seg(u, 7.6, 9.4)
        for k in range(9): smiley(f, 860 + (k % 3) * 95, 180 + (k // 3) * 95, a * b, 0.55, mood="neutral", key=40 + k, fill=(240, 241, 243), stroke=GREY)
        f.text(955, 455, "the same tokens pay for", hand(20, light=True), GREY, a * b, "mm")
        f.text(955, 482, "8.8 independent agents", hand(22, True), INK, a * b, "mm")
        v = seg(u, 10, 11.5)
        f.srect(870, 505, 870 + 170 * v, 529, INK, YEL, a * v, 2, 14); f.text(1052, 517, "vote", hand(20, True), INK, a * v, "lm")
        say(f, u, 8.2, 16.2, "... but a plain vote over independent answers already explains most of the gain.", y=640, size=26)
    elif t < 44.5:                                # S3
        u = t - 24; a = seg(u, 0.2, 1.0) * (1 - seg(u, 19.6, 20.4))
        heading(f, u, 0, 20.4, "Grade the group at equal budget")
        f.text(W / 2, 130, "a run that spends k tokens costs n_B = k / c_1 independent agents", hand(28, True), BLUE, a * seg(u, 0.6, 1.6), "mm")
        lit = (u > 3.5) + (u > 6.5) + (u > 9.5)
        stairs(f, 310, 450, a, lit, w=220, key=60)
        f.sline(290, 450 - 190 - 18, 990, 450 - 190 - 18, RED, a * seg(u, 11, 12), 2.5, dash=9)
        f.text(1005, 450 - 190 - 18, "pass@n", hand(22, True), RED, a * seg(u, 11, 12), "lm")
        f.text(310, 528, "votes, judges and verifiers only pick among answers the agents gave,", hand(22, light=True), GREY, a * seg(u, 11.5, 12.5), "la")
        f.text(310, 560, "so none of them can climb above pass@n at equal cost", hand(22, light=True), GREY, a * seg(u, 11.5, 12.5), "la")
        say(f, u, 13.5, 20.2, "Level 3 needs correct answers that no single agent produced.", y=640, size=30, col=GREEN)
    elif t < 66.5:                                # S4
        u = t - 44; a = seg(u, 0.2, 1.0) * (1 - seg(u, 21.6, 22.4))
        heading(f, u, 0, 22.4, "Move facts, not arguments")
        f.text(70, 115, "HiddenBench: each of four Qwen3.8-27B agents holds part of the decisive facts", hand(22, light=True), GREY, a, "la")
        pts = [(200, 240), (430, 240), (200, 440), (430, 440)]; L = "ABCD"; fw = u >= 10.5
        for i, p in enumerate(pts):
            got = 4 if (fw and u > 13.5 + i * 0.3) else 1
            smiley(f, *p, a, 0.9, "happy" if got == 4 else "neutral", key=80 + i)
            hold = [i] + ([j for j in range(4) if j != i] if got == 4 else [])
            for k, j in enumerate(hold): sticky(f, p[0] - 52 + k * 35, p[1] + 60, L[j], a, 0.85, key=90 + i * 4 + k)
        if not fw:
            for i in range(4):
                for j in range(4):
                    if i != j:
                        ph = (u * 0.5 + (i * 4 + j) * 0.07) % 1
                        bubble(f, lerp(pts[i][0], pts[j][0], ph), lerp(pts[i][1], pts[j][1], ph), a, key=i * 4 + j)
            f.text(315, 560, "debate: answers and reasons", hand(24, True), PURP, a * seg(u, 1, 2), "mm")
        else:
            for i in range(4):
                for j in range(4):
                    if i != j:
                        ph = clamp((u - 11 - i * 0.4) / 2.2)
                        if 0 < ph < 1: sticky(f, lerp(pts[i][0], pts[j][0], ph), lerp(pts[i][1], pts[j][1], ph), L[i], a, 0.75, key=i)
            f.text(315, 560, "fact forwarding: the facts, verbatim", hand(24, True), GREEN, a * seg(u, 11, 12), "mm")
        lv = 3 if (fw and u > 14) else 2
        stairs(f, 640, 430, a, 3, w=180, hs=(60, 110, 160), labels=False, key=120)
        mx = 640 + (lv - 1) * 180 + 90; my = 430 - (60, 110, 160)[lv - 1] - 40
        smiley(f, mx, my, a, 0.6, "happy" if lv == 3 else "neutral", key=130)
        if not fw:
            f.text(910, 500, "0.688 accuracy vs 0.703 pass@n", hand(24, True), PURP, a * seg(u, 3, 4), "mm")
            f.text(910, 534, "stuck at level 2", hand(22, light=True), GREY, a * seg(u, 3, 4), "mm")
        else:
            f.text(910, 500, "0.959 accuracy vs 0.649 pass@n", hand(24, True), GREEN, a * seg(u, 14, 15), "mm")
            f.text(910, 534, "31 points above pass@n, level 3", hand(22, True), INK, a * seg(u, 14.5, 15.5), "mm")
        say(f, u, 16, 22.2, "When everyone sees the whole task, debate does not beat the vote.", y=650, size=24, col=GREY, bold=False)
    elif t < 84.5:                                # S5
        u = t - 66; a = seg(u, 0.2, 1.0) * (1 - seg(u, 17.6, 18.4))
        heading(f, u, 0, 18.4, "Organization emerges, and it costs tokens")
        f.text(70, 115, "each agent may read one message, and may give that budget away", hand(22, light=True), GREY, a, "la")
        hub = (360, 360); oth = [(170, 230), (170, 490), (550, 230)]
        smiley(f, *hub, a, 1.15, "happy" if u > 7 else "neutral", key=150)
        for i, p in enumerate(oth): smiley(f, *p, a, 0.85, key=151 + i)
        for i, p in enumerate(oth):
            ph = clamp((u - 2 - i * 0.5) / 2.2)
            if 0 < ph < 1: coin(f, lerp(p[0], hub[0], ph), lerp(p[1], hub[1], ph), "+1", a, key=160 + i)
            ph2 = clamp((u - 5.2 - i * 0.4) / 2)
            if 0 < ph2 < 1: sticky(f, lerp(p[0], hub[0], ph2), lerp(p[1], hub[1], ph2), "BCD"[i], a, 0.8, key=170 + i)
        f.text(hub[0], hub[1] + 70, "a hub reads every fact", hand(22, True), RED, a * seg(u, 7, 8), "mm")
        f.text(900, 200, "+18 points", hand(56, True), GREEN, a * seg(u, 8, 9), "mm")
        f.text(900, 248, "over a group without transfers", hand(22, light=True), GREY, a * seg(u, 8, 9), "mm")
        c = seg(u, 10, 12)
        f.srect(720, 300, 720 + 360 * 0.67 * c, 330, INK, (246, 206, 200), a * c, 2, 180)
        f.srect(720 + 360 * 0.67 * c, 300, 720 + 360 * c, 330, INK, GREENF, a * c, 2, 181)
        f.text(720 + 120, 352, "coordination", hand(20, True), RED, a * c, "mm"); f.text(720 + 300, 352, "work", hand(20, True), GREEN, a * c, "mm")
        f.text(900, 392, "about two thirds of the tokens go to coordination", hand(21, light=True), GREY, a * c, "mm")
        n = seg(u, 13, 14)
        f.srect(760, 430, 830, 520, INK, (255, 255, 255), a * n, 2, 182)
        for k in range(4): f.sline(772, 450 + k * 17, 818, 450 + k * 17, LIGHT, a * n, 2, key=183 + k, passes=1)
        f.text(850, 450, "a prompt the model writes from the rules", hand(21, True), INK, a * n, "la")
        f.text(850, 480, "describes the same hub and reaches level 3", hand(21, True), INK, a * n, "la")
        f.text(850, 510, "at less than half the budget (descriptive)", hand(21, light=True), GREY, a * n, "la")
    elif t < 102.5:                               # S6
        u = t - 84; a = seg(u, 0.2, 1.0) * (1 - seg(u, 17.6, 18.4))
        heading(f, u, 0, 18.4, "The group trains its next generation")
        steps = ["play fresh tasks", "check, no labels", "train candidates", "select", "confirm", "release"]
        cx, cy, R = 290, 360, 135
        for i, s in enumerate(steps):
            ang = -math.pi / 2 + i / 6 * 2 * math.pi; x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
            on = int((u * 1.1) % 6) == i
            f.scircle(x, y, 10, BLUE if on else GREY, YEL if on else (255, 255, 255), a, 2, key=200 + i)
            right = math.cos(ang) >= -0.1
            f.text(x + (18 if right else -18), y, s, hand(19, on), INK if on else GREY, a, "lm" if right else "rm")
        smiley(f, cx, cy, a, 0.9, key=210)
        charts = [("PlanBench", [0.613, 0.857, 0.937, 0.940, 0.950], 0, 1, BLUE, "0.613 to 0.950"),
                  ("HiddenBench (T3k)", [0.509, 0.713, 0.791, 0.811, 0.845, 0.886], 0.4, 1, PURP, "0.509 to 0.886"),
                  ("Hanabi, score / 25", [0, 0.678, 2.953, 4.110, 4.420, 4.523, 4.482], 0, 5, RED, "0 to 4.5")]
        for k, (nm, v, lo, hi, col, lab) in enumerate(charts):
            x0, y0, cw, ch = 640 + k * 210, 220, 170, 210
            f.text(x0, y0 - 22, nm, hand(21, True), INK, a, "la")
            f.sline(x0, y0 + ch, x0 + cw, y0 + ch, INK, a, 2, key=220 + k); f.sline(x0, y0, x0, y0 + ch, INK, a, 2, key=230 + k)
            g = seg(u, 2 + k * 1.2, 9 + k * 1.2) * (len(v) - 1)
            P = [(x0 + i * cw / (len(v) - 1), y0 + ch - (v[i] - lo) / (hi - lo) * ch * 0.92) for i in range(len(v))]
            for i in range(len(v) - 1):
                if g > i:
                    q = clamp(g - i); f.sline(P[i][0], P[i][1], lerp(P[i][0], P[i + 1][0], q), lerp(P[i][1], P[i + 1][1], q), col, a, 3.5, key=240 + k * 10 + i, passes=1)
            for i, p in enumerate(P):
                if g >= i: f.dot(p[0], p[1], 5, col, a)
            f.text(x0 + cw / 2, y0 + ch + 30, lab, hand(22, True), col, a * seg(u, 9 + k, 10 + k), "mm")
        say(f, u, 11, 18.2, "Trained only on outputs their own protocol accepts, every released generation", y=600, size=24)
        say(f, u, 11, 18.2, "beats its predecessor on unseen tasks, for four to six generations.", y=636, size=24)
    else:                                         # S7
        u = t - 102; a = seg(u, 0.2, 1.2) * (1 - seg(u, 7.4, 8.0))
        for i in range(4): smiley(f, 470 + i * 110, 200, a, 0.7, "happy", key=300 + i)
        f.text(W / 2, 330, "A group outperforms its members when it moves information", hand(32, True), INK, a, "mm")
        f.text(W / 2, 376, "more efficiently than it spends tokens on coordination,", hand(32, True), INK, a, "mm")
        f.text(W / 2, 422, "and it can learn to do so from its own work.", hand(32, True), BLUE, a, "mm")
        f.text(W / 2, 520, "lixuan27.github.io/RCI", hand(26, light=True), GREY, a, "mm")
    return f.out()

# ------------------------------------------------------------------ ladder (~30 s)
PROTOS = [("Blackboard", -0.331, PURP), ("Debate, 2 rounds", -0.015, PURP), ("Blackboard + hint", 0.043, PURP), ("Debate, 2 rounds + hint", 0.079, PURP),
          ("Debate, 3 rounds + hint", 0.109, PURP), ("Facts-only blackboard", 0.137, GREEN), ("Shared context", 0.190, GREEN), ("Gated blackboard", 0.234, GREEN),
          ("Fact forwarding", 0.310, GREEN), ("Shared context + forwarding", 0.328, GREEN)]
def ladder_video(t):
    f = F(); a = seg(t, 0.2, 1.0) * (1 - seg(t, 29.2, 30))
    heading(f, t, 0, 30, "Where protocols land on the ladder")
    f.text(70, 108, "HiddenBench, four Qwen3.8-27B agents, split facts: accuracy minus pass@n_B of independent agents", hand(21, light=True), GREY, a, "la")
    x0, x1, y0, rh = 540, 1180, 165, 44
    X = lambda m: lerp(x0, x1, (m + 0.36) / 0.72)
    f.srect(X(0), y0 - 14, x1, y0 + rh * 10, GREEN, GREENF, a * 0.6, 1.5, key=1)
    f.sline(X(0), y0 - 24, X(0), y0 + rh * 10 + 8, RED, a, 2.5, dash=8)
    f.text(X(0), y0 + rh * 10 + 30, "pass@n_B", hand(20, True), RED, a, "mm")
    f.text(x1 - 10, y0 + 4, "level 3 lives here", hand(20, True), GREEN, a, "rm")
    for i, (nm, m, col) in enumerate(PROTOS):
        y = y0 + i * rh + 12; ap = seg(t, 2 + i * 2.2, 3 + i * 2.2)
        f.text(x0 - 22, y, nm, hand(21, True), col, a * ap, "rm")
        xm = lerp(X(0), X(m), ease(clamp((t - 2.3 - i * 2.2) / 1.2)))
        f.sline(X(0), y, xm, y, col, a * ap, 7, key=10 + i, passes=1)
        f.scircle(xm, y, 9, col, (255, 255, 255), a * ap, 2.5, key=20 + i)
        f.text(xm + 18 if m >= 0 else X(0) + 18, y, f"{m:+.3f}", hand(18, True), INK, a * seg(t, 3.4 + i * 2.2, 4 + i * 2.2), "lm")
    say(f, t, 24, 30, "Trading arguments stays at level 2; passing facts on climbs above pass@n.", y=680, size=24, col=INK)
    return f.out()

# ------------------------------------------------------------------ chain (~36 s)
ROUNDS = [(1, 0.4913, 0.6946, 0.203, "G1"), (2, 0.7344, 0.7788, 0.044, "G2"), (3, 0.8069, 0.8075, 0.001, None), (4, 0.7800, 0.8238, 0.044, "G3"),
          (5, 0.7900, 0.8550, 0.065, "G4"), (6, 0.8250, 0.8263, 0.001, None), (7, 0.8237, 0.8700, 0.046, "G5"), (8, 0.9038, 0.9183, 0.015, None)]
def chain_video(t):
    f = F(); a = seg(t, 0.2, 1.0) * (1 - seg(t, 35.2, 36))
    heading(f, t, 0, 36, "One release at a time")
    f.text(70, 108, "HiddenBench chain T3k: each round, a candidate meets the current generation on fresh confirmation seeds", hand(21, light=True), GREY, a, "la")
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
        f.text(250, 580, "needs more than 0.026", hand(20, light=True), GREY, a * dv, "mm")
        v = seg(u, 2.3, 2.8)
        if rel: f.check(120, 640, GREEN, a * v); f.text(150, 640, f"released as {rel}", hand(26, True), GREEN, a * v, "lm")
        else: f.cross(120, 640, RED, a * v, 0.8); f.text(150, 640, "flat round: keep the current one", hand(24, True), RED, a * v, "lm")
    gx0, gy = 560, 300
    vals = [0.509, 0.713, 0.791, 0.811, 0.845, 0.886]
    for k in range(6):
        x = gx0 + k * 118; on = k <= gen
        smiley(f, x, gy, a, 0.62, "happy" if on else "neutral", key=600 + k, fill=BLUEF if on else (243, 243, 241), stroke=BLUE if on else LIGHT)
        f.text(x, gy + 46, f"G{k}", hand(20, True), INK if on else LIGHT, a, "mm")
        if on: f.text(x, gy + 74, f"{vals[k]:.3f}", hand(18, light=True), GREY, a, "mm")
        if k < 5: f.arrow(x + 30, gy, x + 86, gy, BLUE if k < gen else LIGHT, a, 2.2, 10, key=610 + k)
    f.text(gx0 + 295, gy + 112, "group accuracy on the selection set", hand(19, light=True), GREY, a, "mm")
    f.text(gx0 + 295, 520, "Five releases in eight rounds; three flat rounds keep the incumbent.", hand(23, True), INK, a * seg(t, 31, 32), "mm")
    f.text(gx0 + 295, 556, "Fresh seeds every round stop selection on the noise of a reused set.", hand(21, light=True), GREY, a * seg(t, 31.5, 32.5), "mm")
    return f.out()

SCENES = {"overview": (overview, 110), "ladder": (ladder_video, 30), "chain": (chain_video, 36)}
SCRATCH = "."

def render(name, out, preview=None):
    fn, dur = SCENES[name]
    if preview is not None:
        fn(preview).save(out); return
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
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
