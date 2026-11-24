#!/usr/bin/env python3
"""Sum up 24 November 2026's world news in one image.

Renders a newspaper front page (1024x1024 PNG) to /output/entry.png.
Pure Python 3 standard library: no network, no third-party packages,
no timestamps, no randomness -- two runs write identical bytes.

Layout: masthead, lead story (Nvidia / Huang), second story (space
weapons), six more stories in two rows, a markets bar chart, footer.
"""

import os
import struct
import zlib

W = 1024
H = 1024
OUT_PATH = "/output/entry.png"

# ---- palette (newsprint) ----
PAPER = (248, 244, 236)
INK = (24, 24, 24)
NAVY = (26, 48, 80)
RED = (178, 34, 34)
BLUE = (36, 80, 140)
GRAY = (112, 110, 102)
FAINT = (233, 227, 214)
GREEN = (22, 120, 60)
DARKRED = (150, 20, 20)
WHITE = (255, 255, 255)
GOLD = (176, 132, 40)

# ---- framebuffer: RGB, row-major ----
buf = bytearray(W * H * 3)


def fill(color):
    r, g, b = color
    buf[0::3] = bytes([r]) * (W * H)
    buf[1::3] = bytes([g]) * (W * H)
    buf[2::3] = bytes([b]) * (W * H)


def px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = color


def fill_rect(x, y, w, h, color):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    r, g, b = color
    row = bytes([r, g, b]) * (x1 - x0)
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        buf[i:i + len(row)] = row


def hline(x, y, w, color, t=1):
    fill_rect(x, y, w, t, color)


def vline(x, y, h, color, t=1):
    fill_rect(x, y, t, h, color)


def rect_outline(x, y, w, h, color, t=1):
    hline(x, y, w, color, t)
    hline(x, y + h - t, w, color, t)
    vline(x, y, h, color, t)
    vline(x + w - t, y, h, color, t)


def line(x0, y0, x1, y1, color):
    """Bresenham line."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        px(x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def disc(cx, cy, r, color):
    """Filled circle."""
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        hline(cx - dx, cy + dy, 2 * dx + 1, color)


def ring(cx, cy, r, color, t=2):
    """Circle outline, drawn as concentric rings."""
    for rr in range(r - t + 1, r + 1):
        for dy in range(-rr, rr + 1):
            dx = int((rr * rr - dy * dy) ** 0.5)
            px(cx - dx, cy + dy, color)
            px(cx + dx, cy + dy, color)


def triangle(x0, y0, x1, y1, x2, y2, color):
    """Filled triangle via scanlines."""
    ys = sorted([(x0, y0), (x1, y1), (x2, y2)], key=lambda p: p[1])
    (ax, ay), (bx, by), (cx, cy) = ys

    def interp(xa, ya, xb, yb, y):
        if yb == ya:
            return xa
        return xa + (xb - xa) * (y - ya) / (yb - ya)

    for y in range(ay, cy + 1):
        if y < by:
            xa = interp(ax, ay, bx, by, y)
            xb = interp(ax, ay, cx, cy, y)
        else:
            xa = interp(bx, by, cx, cy, y)
            xb = interp(ax, ay, cx, cy, y)
        hline(int(min(xa, xb)), y, int(abs(xb - xa)) + 1, color)


# ---- PNG encoding (deterministic: no metadata chunks) ----

def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def png_bytes():
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += buf[y * W * 3:(y + 1) * W * 3]
    idat = zlib.compress(bytes(raw), 9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", idat)
        + _chunk(b"IEND", b"")
    )


# ---- 5x7 bitmap font: each glyph is 7 rows of 5 bits ----
# Written as binary literals, bit 4 = leftmost pixel.
FONT = {
    "A": (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "B": (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    "D": (0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "J": (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "K": (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": (0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    "Q": (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    "W": (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010),
    "X": (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    "Z": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    "0": (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    "1": (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "2": (0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111),
    "3": (0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110),
    "4": (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    "5": (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    "6": (0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    "7": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    "8": (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    "9": (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0b01100, 0b01100),
    ",": (0, 0, 0, 0, 0b01100, 0b00100, 0b01000),
    ":": (0, 0b01100, 0b01100, 0, 0b01100, 0b01100, 0),
    ";": (0, 0b01100, 0b01100, 0, 0b01100, 0b00100, 0b01000),
    "!": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0, 0b00100),
    "?": (0b01110, 0b10001, 0b00001, 0b00110, 0b00100, 0, 0b00100),
    "'": (0b00100, 0b00100, 0b01000, 0, 0, 0, 0),
    '"': (0b01010, 0b01010, 0, 0, 0, 0, 0),
    "-": (0, 0, 0, 0b01110, 0, 0, 0),
    "(": (0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010),
    ")": (0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000),
    "/": (0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000),
    "%": (0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011),
    "$": (0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100),
    "+": (0, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0),
    "=": (0, 0, 0b11111, 0, 0b11111, 0, 0),
    "*": (0, 0b10101, 0b01110, 0b11111, 0b01110, 0b10101, 0),
    "#": (0b01010, 0b01010, 0b11111, 0b01010, 0b11111, 0b01010, 0b01010),
    "&": (0b01100, 0b10010, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101),
    "<": (0b00001, 0b00010, 0b00100, 0b01000, 0b00100, 0b00010, 0b00001),
    ">": (0b10000, 0b01000, 0b00100, 0b00010, 0b00100, 0b01000, 0b10000),
    "_": (0, 0, 0, 0, 0, 0, 0b11111),
    "@": (0b01110, 0b10001, 0b10111, 0b10101, 0b10110, 0b10000, 0b01110),
    "[": (0b01110, 0b01000, 0b01000, 0b01000, 0b01000, 0b01000, 0b01110),
    "]": (0b01110, 0b00010, 0b00010, 0b00010, 0b00010, 0b00010, 0b01110),
    "|": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "\\": (0b10000, 0b01000, 0b01000, 0b00100, 0b00010, 0b00010, 0b00001),
}

# Normalise curly punctuation to the ASCII glyphs above.
NORMALISE = {
    "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u00b7": ".", "\u00d7": "x",
    "\u2212": "-", "\u2011": "-", "\u00a0": " ",
}


def norm_char(ch):
    if ch in FONT:
        return ch
    if ch in NORMALISE:
        return NORMALISE[ch]
    if ch.islower():
        return ch.upper()
    return "?"


def glyph_width(scale):
    return 6 * scale


def text_width(s, scale):
    s = "".join(norm_char(c) for c in s)
    if not s:
        return 0
    return len(s) * glyph_width(scale) - scale


def draw_glyph(x, y, ch, scale, color, bold=False):
    rows = FONT[norm_char(ch)]
    off = 1 if bold and scale >= 2 else 0
    for r in range(7):
        bits = rows[r]
        for c in range(5):
            if bits >> (4 - c) & 1:
                fill_rect(x + c * scale, y + r * scale, scale, scale, color)
                if off:
                    fill_rect(x + c * scale + off, y + r * scale,
                              scale, scale, color)


def draw_text(x, y, s, scale, color, bold=False):
    cx = x
    for ch in s:
        draw_glyph(cx, y, ch, scale, color, bold)
        cx += glyph_width(scale)
    return cx


def draw_text_centered(cx, y, s, scale, color, bold=False):
    draw_text(cx - text_width(s, scale) // 2, y, s, scale, color, bold)


def draw_text_right(x, y, s, scale, color, bold=False):
    draw_text(x - text_width(s, scale), y, s, scale, color, bold)


def wrap_lines(text, scale, max_w):
    """Greedy word wrap; returns a list of lines (no trailing spaces)."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            # hard-split a single over-long word
            while text_width(word, scale) > max_w:
                cut = max_w // glyph_width(scale)
                lines.append(word[:cut])
                word = word[cut:]
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_para(x, y, max_w, text, scale, color, leading=None, bold=False):
    """Draw a wrapped paragraph; returns the y just past the last line."""
    if leading is None:
        leading = 7 * scale + 2
    for ln in wrap_lines(text, scale, max_w):
        draw_text(x, y, ln, scale, color, bold)
        y += leading
    return y


# ---- editorial icons (small geometric drawings) ----

def icon_chip(cx, cy, s, color):
    """A computer chip: square body, pins, inner die."""
    body = 16 * s
    x0, y0 = cx - body // 2, cy - body // 2
    fill_rect(x0, y0, body, body, color)
    fill_rect(x0 + 4 * s, y0 + 4 * s, body - 8 * s, body - 8 * s, PAPER)
    fill_rect(x0 + 6 * s, y0 + 6 * s, body - 12 * s, body - 12 * s, color)
    for i in range(4):
        off = (3 + i * 4) * s
        fill_rect(x0 + off, y0 - 3 * s, 2 * s, 3 * s, color)
        fill_rect(x0 + off, y0 + body, 2 * s, 3 * s, color)
        fill_rect(x0 - 3 * s, y0 + off, 3 * s, 2 * s, color)
        fill_rect(x0 + body, y0 + off, 3 * s, 2 * s, color)


def icon_satellite(cx, cy, s, color):
    """Satellite with solar panels, antenna and a few stars."""
    fill_rect(cx - 8 * s, cy - 3 * s, 16 * s, 6 * s, color)
    fill_rect(cx - 22 * s, cy - 2 * s, 13 * s, 4 * s, color)
    fill_rect(cx + 9 * s, cy - 2 * s, 13 * s, 4 * s, color)
    line(cx - 9 * s, cy, cx - 22 * s, cy, color)
    line(cx + 8 * s, cy, cx + 22 * s, cy, color)
    line(cx, cy - 3 * s, cx + 7 * s, cy - 12 * s, color)
    disc(cx + 8 * s, cy - 13 * s, 2 * s, RED)
    disc(cx - 26 * s, cy - 10 * s, 1 * s, color)
    disc(cx + 26 * s, cy + 8 * s, 1 * s, color)
    disc(cx - 24 * s, cy + 12 * s, 1 * s, color)


def icon_scales(cx, cy, s, color):
    """Scales of justice."""
    vline(cx, cy - 14 * s, 28 * s, color, 2 * s)
    hline(cx - 14 * s, cy - 14 * s, 28 * s, color, 2 * s)
    line(cx - 14 * s, cy - 14 * s, cx - 14 * s, cy + 6 * s, color)
    line(cx + 14 * s, cy - 14 * s, cx + 14 * s, cy + 6 * s, color)
    triangle(cx - 20 * s, cy + 6 * s, cx - 8 * s, cy + 6 * s,
             cx - 14 * s, cy + 14 * s, color)
    triangle(cx + 8 * s, cy + 6 * s, cx + 20 * s, cy + 6 * s,
             cx + 14 * s, cy + 14 * s, color)
    hline(cx - 8 * s, cy + 14 * s, 16 * s, color, 2 * s)


def icon_globe(cx, cy, s, color):
    """Globe with a rising heat arrow."""
    ring(cx, cy, 16 * s, color, 2 * s)
    line(cx - 16 * s, cy, cx + 16 * s, cy, color)
    line(cx, cy - 16 * s, cx, cy + 16 * s, color)
    line(cx, cy + 16 * s, cx + 6 * s, cy + 24 * s, RED)
    line(cx + 6 * s, cy + 24 * s, cx + 12 * s, cy + 18 * s, RED)
    triangle(cx + 8 * s, cy + 12 * s, cx + 16 * s, cy + 12 * s,
             cx + 12 * s, cy + 4 * s, RED)


def icon_burst(cx, cy, s, color):
    """Starburst: radiating lines from a centre."""
    disc(cx, cy, 4 * s, color)
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1),
                   (1, 1), (-1, -1), (1, -1), (-1, 1),
                   (2, 1), (-2, -1), (2, -1), (-2, 1),
                   (1, 2), (-1, -2), (1, -2), (-1, 2)]:
        line(cx, cy, cx + dx * 9 * s, cy + dy * 9 * s, color)


def icon_microbe(cx, cy, s, color):
    """Round microbe with spikes."""
    disc(cx, cy, 10 * s, color)
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1),
                   (1, 1), (-1, -1), (1, -1), (-1, 1)]:
        line(cx + dx * 8 * s, cy + dy * 8 * s,
             cx + dx * 15 * s, cy + dy * 15 * s, color)
    disc(cx - 3 * s, cy - 2 * s, 2 * s, PAPER)
    disc(cx + 3 * s, cy + 3 * s, 2 * s, PAPER)


def icon_cross(cx, cy, s, color):
    """Medical cross in a ring."""
    ring(cx, cy, 15 * s, color, 2 * s)
    fill_rect(cx - 3 * s, cy - 9 * s, 6 * s, 18 * s, RED)
    fill_rect(cx - 9 * s, cy - 3 * s, 18 * s, 6 * s, RED)


def icon_quake(cx, cy, s, color):
    """Seismograph zig-zag in a frame."""
    rect_outline(cx - 20 * s, cy - 12 * s, 40 * s, 24 * s, color, 2 * s)
    pts = [(-18, 0), (-12, 0), (-9, -8), (-6, 8), (-3, -4),
           (0, 4), (3, -9), (6, 9), (9, 0), (12, 0), (18, 0)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        line(cx + ax * s, cy + ay * s, cx + bx * s, cy + by * s, color)


# ---- story column renderer ----

def story_column(x, y, w, kicker, headline, body, rule_color,
                 head_scale=3, body_scale=2):
    """Kicker + headline + body; returns y past the column."""
    hline(x, y, w, rule_color, 3)
    y += 10
    draw_text(x, y, kicker, 2, RED, bold=True)
    y += 20
    y = draw_para(x, y, w, headline, head_scale, INK,
                  leading=7 * head_scale + 4, bold=True)
    y += 6
    y = draw_para(x, y, w, body, body_scale, INK,
                  leading=7 * body_scale + 2)
    return y


# ---- the day's news: Tuesday 24 November 2026 ----
# Facts as reported on the day; copy kept short so the page stays legible.

LEAD_KICKER = "TECHNOLOGY . MARKETS"
LEAD_HEAD = "HUANG IS BACK AT NVIDIA"
LEAD_BODY = (
    "Nvidia reinstates Jensen Huang as chief executive less than two "
    "weeks after he resigned, after Donald Trump intervened. Shares "
    "surge and Wall Street posts its best day in over a year, with the "
    "Nasdaq up 6.5% and Seoul stocks up more than 6%."
)

SPACE_KICKER = "SECURITY"
SPACE_HEAD = "A NUCLEAR WEAPON IN ORBIT?"
SPACE_BODY = (
    "NATO chief Mark Rutte vows the alliance will defend space after "
    "reports Russia may launch a nuclear-armed satellite. Moscow warns "
    "of a 'preventive nuclear attack'."
)

ROW2 = [
    ("JUSTICE",
     "MYANMAR GUILTY OF GENOCIDE",
     "The court rules Myanmar committed genocide against the Rohingya. "
     "Fourteen nations back it; Britain sanctions its generals.",
     BLUE),
    ("CLIMATE",
     "CLIMATE SUMMIT ENDS IN FAILURE",
     "The UN climate summit closes without a deal after a split over "
     "fossil fuels and climate finance.",
     GOLD),
    ("MIDDLE EAST",
     "GAZA STRIKES KILL SIX",
     "Israeli strikes kill at least six Palestinians, two of them "
     "police. The UN says the war undid 77 years of development.",
     DARKRED),
]

ROW3 = [
    ("HEALTH",
     "EBOLA TEAMS TRAPPED",
     "Heavy fighting near a hospital in Ituri, DR Congo, forces Ebola "
     "responders to take cover for over 24 hours.",
     RED),
    ("HEALTH",
     "US LOSES MEASLES STATUS",
     "The US loses measles-free status after 25 years, as a "
     "Pennsylvania outbreak claims a ninth life.",
     RED),
    ("ASIA",
     "QUAKE SHAKES NEPAL",
     "A magnitude 5.4 quake strikes Nepal's Koshi province; tremors "
     "felt in India, Bhutan and Bangladesh.",
     BLUE),
]

# (name, change in percent) for the markets chart
MARKETS = [
    ("NASDAQ", 6.51),
    ("S&P 500", 4.73),
    ("NIKKEI", 3.91),
    ("SEOUL", 6.00),
    ("DAX", 2.15),
    ("CAC 40", 1.48),
    ("FTSE", 1.30),
    ("HANG SENG", -0.62),
    ("BRENT", -2.99),
]

FOOTER = (
    "ALSO: Guterres urges AI safety rules within a year . Sanofi to buy "
    "Insmed for $41bn . US states sue Musk firms over Grok images"
)


def render():
    fill(PAPER)
    rect_outline(10, 10, W - 20, H - 20, INK, 2)
    rect_outline(16, 16, W - 32, H - 32, INK, 1)

    # ---- masthead ----
    fill_rect(16, 24, W - 32, 72, NAVY)
    draw_text_centered(W // 2, 34, "THE WORLD", 7, WHITE, bold=True)
    draw_text_centered(W // 2, 104,
                       "TUESDAY, 24 NOVEMBER 2026", 2, INK, bold=True)
    draw_text_centered(W // 2, 122,
                       "ONE IMAGE . THE WHOLE DAY'S NEWS", 2, GRAY)
    hline(28, 140, W - 56, INK, 2)

    # ---- lead row ----
    # Lead story, left; chip icon at its top right.
    y = 154
    draw_text(28, y, LEAD_KICKER, 2, RED, bold=True)
    y += 22
    y = draw_para(28, y, 420, LEAD_HEAD, 4, INK, leading=32, bold=True)
    y += 8
    draw_para(28, y, 420, LEAD_BODY, 2, INK, leading=16)
    icon_chip(528, 240, 3, NAVY)

    # Space story, right column.
    vline(636, 154, 252, GRAY, 1)
    icon_satellite(816, 184, 2, NAVY)
    y2 = 234
    draw_text(652, y2, SPACE_KICKER, 2, RED, bold=True)
    y2 += 22
    y2 = draw_para(652, y2, 344, SPACE_HEAD, 3, INK, leading=25, bold=True)
    y2 += 6
    draw_para(652, y2, 344, SPACE_BODY, 2, INK, leading=16)

    hline(28, 420, W - 56, INK, 2)

    # ---- row 2: three stories ----
    col_w = 304
    xs = [28, 356, 684]
    y = 436
    for (kicker, head, body, rule), x in zip(ROW2, xs):
        story_column(x, y, col_w, kicker, head, body, rule)

    hline(28, 624, W - 56, INK, 1)

    # ---- row 3: three stories ----
    y = 640
    for (kicker, head, body, rule), x in zip(ROW3, xs):
        story_column(x, y, col_w, kicker, head, body, rule)

    hline(28, 828, W - 56, INK, 2)

    # ---- markets chart ----
    # All bars rise from one baseline; gains are green, losses red, and
    # the sign is also printed, so nothing collides below the baseline.
    y = 844
    draw_text(28, y, "MARKETS: THE HUANG RALLY", 2, INK, bold=True)
    draw_text_right(996, y, "GOLD $3,620", 2, GRAY)
    base = 920
    top = 868
    slot = (W - 56) // len(MARKETS)
    for i, (name, chg) in enumerate(MARKETS):
        cx = 28 + slot * i + slot // 2
        h = int(abs(chg) / 6.51 * (base - top - 8))
        color = GREEN if chg >= 0 else DARKRED
        fill_rect(cx - 26, base - h, 52, h, color)
        label = ("+" if chg >= 0 else "") + ("%.2f%%" % chg)
        draw_text_centered(cx, base - h - 14, label, 1, color, bold=True)
        draw_text_centered(cx, base + 8, name, 1, INK)
    hline(28, base, W - 56, INK, 2)

    hline(28, 962, W - 56, INK, 1)
    draw_para(28, 972, W - 56, FOOTER, 2, GRAY, leading=15)


def main():
    render()
    data = png_bytes()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes, %dx%d)" % (OUT_PATH, len(data), W, H))


if __name__ == "__main__":
    main()
