#!/usr/bin/env python3
"""Generate 8-bit RPG style SVGs for the GitHub profile README.

Usage:
    python scripts/generate.py            # fetch stats with $GITHUB_TOKEN
    python scripts/generate.py --offline  # use dummy stats (local preview)
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import os
import re
import sys
import tomllib
import unicodedata
import urllib.request
from html import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import readings  # noqa: E402
import sprites  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "assets/fonts/DotGothic16-Regular.ttf"
CONFIG_PATH = ROOT / "profile.toml"
DIST = ROOT / "dist"
README = ROOT / "README.md"

BLACK = "#000000"
WHITE = "#fcfcfc"
YELLOW = "#f8b800"
GREEN = "#58d854"
RED = "#d82800"
GRAY = "#3c3c3c"
FONT_FAMILY = "PixelJP"


# --------------------------------------------------------------------------- themes
def four_tone(l0: str, l1: str, l2: str, l3: str) -> dict:
    """Handheld-era 4-shade palette (l0 = lightest ... l3 = darkest)."""
    return dict(
        bg=l0, fg=l3, accent=l2, dim=l1, muted=l2, fill=l3, gauge=(l3, l3, l3), double=True,
        sky=[(0, 60, l1), (60, 150, l0)], dither=[(60, l1)],
        mountain=l2, cap=l0, hill=l1, grass=(l0, l1, l2), horizon=l3,
        title=l3, title_shadow=l0, title_stroke=l3,
        sprite={
            "K": l3, "W": l0, "S": l0, "B": l2, "b": l1, "Y": l1, "R": l2, "r": l1,
            "L": l2, "G": l2, "g": l1, "E": l2, "e": l1, "f": l0,
            "N": l2, "n": l1, "T": l1, "t": l0,
        },
    )


THEMES = {
    # NES-like full color: black windows with white frames
    "nes": dict(
        bg=BLACK, fg=WHITE, accent=YELLOW, dim=GRAY, muted="#9c9c9c", fill=YELLOW,
        gauge=(GREEN, YELLOW, RED), double=False,
        sky=[(0, 50, "#3cbcfc"), (50, 96, "#6cc8fc"), (96, 150, "#a4e4fc")],
        dither=[(50, "#3cbcfc"), (96, "#6cc8fc")],
        mountain="#0078f8", cap=WHITE, hill="#00a844",
        grass=("#00a800", "#58d854", "#005800"), horizon="#005800",
        title=YELLOW, title_shadow=BLACK, title_stroke=BLACK, sprite={},
    ),
    # monochrome handheld look: white windows with black double frames
    "mono": four_tone("#f8f8f8", "#a8a8a8", "#585858", "#101010"),
    # green-tinted handheld LCD
    "gb": four_tone("#e0f0c8", "#98b870", "#4a6c48", "#14281c"),
}
T: dict = THEMES["mono"]


def set_theme(name: str) -> None:
    global T
    if name not in THEMES:
        sys.exit(f"unknown theme {name!r}; choose from {', '.join(THEMES)}")
    T = THEMES[name]


# --------------------------------------------------------------------------- font
class Font:
    def __init__(self, path: Path):
        self.path = path
        self.tt = TTFont(path, lazy=True)
        self.cmap = self.tt.getBestCmap()
        self.hmtx = self.tt["hmtx"]
        self.upm = self.tt["head"].unitsPerEm
        hhea = self.tt["hhea"]
        self.ascent = hhea.ascent / self.upm
        self.descent = -hhea.descent / self.upm
        self._cache: dict[frozenset, str] = {}

    def width(self, text: str, size: float) -> float:
        total = 0
        for ch in text:
            gid = self.cmap.get(ord(ch))
            if gid is None:
                total += self.upm if unicodedata.east_asian_width(ch) in "WF" else self.upm / 2
            else:
                total += self.hmtx[gid][0]
        return total / self.upm * size

    def baseline(self, top: float, size: float) -> float:
        """y of the baseline for text whose em box starts at `top`."""
        em = self.ascent + self.descent
        return top + size * (self.ascent / em)

    def missing(self, chars: set[str]) -> set[str]:
        return {c for c in chars if not c.isspace() and ord(c) not in self.cmap}

    def woff2_base64(self, chars: set[str]) -> str:
        key = frozenset(chars)
        if key not in self._cache:
            opts = subset.Options()
            opts.flavor = "woff2"
            opts.layout_features = []
            opts.hinting = False
            opts.desubroutinize = True
            opts.notdef_outline = False
            opts.name_IDs = [0, 1, 2]
            font = subset.load_font(str(self.path), opts)
            sub = subset.Subsetter(opts)
            sub.populate(text="".join(sorted(chars)) or " ")
            sub.subset(font)
            buf = io.BytesIO()
            subset.save_font(font, buf, opts)
            self._cache[key] = base64.b64encode(buf.getvalue()).decode()
        return self._cache[key]


# --------------------------------------------------------------------------- svg
class Svg:
    def __init__(self, font: Font, w: int, h: int, title: str):
        self.font, self.w, self.h, self.title = font, w, h, title
        self.parts: list[str] = []
        self.css: list[str] = []
        self.chars: set[str] = set()

    def add(self, s: str) -> None:
        self.parts.append(s)

    def rect(self, x, y, w, h, fill, extra="") -> None:
        self.add(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{fill}"{extra}/>')

    def text(self, x, top, s, size=20, fill=None, anchor="start", extra="") -> float:
        """Draw text with its em box top at `top`. Returns the rendered width."""
        fill = fill or T["fg"]
        self.chars.update(s)
        y = self.font.baseline(top, size)
        self.add(
            f'<text x="{x:g}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}"{extra}>{escape(s)}</text>'
        )
        return self.font.width(s, size)

    def render(self) -> str:
        missing = self.font.missing(self.chars)
        if missing:
            print(f"warning: glyphs missing in font: {''.join(sorted(missing))}", file=sys.stderr)
        font_css = ""
        if self.chars - {" "}:
            b64 = self.font.woff2_base64(self.chars)
            font_css = (
                f"@font-face{{font-family:'{FONT_FAMILY}';"
                f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
            )
        style = (
            font_css
            + f"text{{font-family:'{FONT_FAMILY}',monospace;white-space:pre;}}"
            + "".join(self.css)
            + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" shape-rendering="crispEdges" role="img" '
            f'aria-label="{escape(self.title)}">'
            f"<title>{escape(self.title)}</title><style>{style}</style>"
            + "".join(self.parts)
            + "</svg>\n"
        )


def sprite(grid: list[str], x: float, y: float, px: int, cls: str = "") -> str:
    """Render a character grid as <rect>s, merging horizontal runs of one color."""
    out = []
    for r, row in enumerate(grid):
        c = 0
        while c < len(row):
            ch = row[c]
            if ch == ".":
                c += 1
                continue
            start = c
            while c < len(row) and row[c] == ch:
                c += 1
            out.append(
                f'<rect x="{x + start * px:g}" y="{y + r * px:g}" width="{(c - start) * px:g}" '
                f'height="{px}" fill="{T["sprite"].get(ch, sprites.COLORS[ch])}"/>'
            )
    attr = f' class="{cls}"' if cls else ""
    return f"<g{attr}>{''.join(out)}</g>"


def cursor_right(x: float, y: float, px: int = 2, fill: str | None = None, cls: str = "") -> str:
    fill = fill or T["fg"]
    rows = [1, 2, 3, 4, 3, 2, 1]
    rects = "".join(
        f'<rect x="{x:g}" y="{y + i * px:g}" width="{n * px:g}" height="{px}" fill="{fill}"/>'
        for i, n in enumerate(rows)
    )
    attr = f' class="{cls}"' if cls else ""
    return f"<g{attr}>{rects}</g>"


def cursor_down(x: float, y: float, px: int = 2, fill: str | None = None, cls: str = "") -> str:
    fill = fill or T["fg"]
    cols = [7, 5, 3, 1]
    rects = "".join(
        f'<rect x="{x + (7 - n) / 2 * px:g}" y="{y + i * px:g}" width="{n * px:g}" height="{px}" fill="{fill}"/>'
        for i, n in enumerate(cols)
    )
    attr = f' class="{cls}"' if cls else ""
    return f"<g{attr}>{rects}</g>"


def window(svg: Svg, x, y, w, h, title: str | None = None, bw: int = 4, inset: int = 4) -> None:
    """Classic RPG window: solid panel, frame with pixel-rounded corners.

    Themes with `double` add a thin inner line (handheld-style double frame).
    With a title, the top border is lowered so the label can sit on it.
    """
    bg, fg = T["bg"], T["fg"]
    svg.rect(x, y, w, h, bg)
    top = 12 if title else inset
    bx, by, bwid, bhei = x + inset, y + top, w - 2 * inset, h - top - inset

    def frame(fx, fy, fw, fh, t):
        svg.rect(fx, fy, fw, t, fg)
        svg.rect(fx, fy + fh - t, fw, t, fg)
        svg.rect(fx, fy, t, fh, fg)
        svg.rect(fx + fw - t, fy, t, fh, fg)

    frame(bx, by, bwid, bhei, bw)
    for cx, cy, dx, dy in (
        (bx, by, 1, 1),
        (bx + bwid - bw, by, -1, 1),
        (bx, by + bhei - bw, 1, -1),
        (bx + bwid - bw, by + bhei - bw, -1, -1),
    ):
        svg.rect(cx, cy, bw, bw, bg)
        svg.rect(cx + dx * bw, cy + dy * bw, bw, bw, fg)
    if T["double"]:
        g = bw + 4
        frame(bx + g, by + g, bwid - 2 * g, bhei - 2 * g, 2)
    if title:
        size = 20
        tw = svg.font.width(title, size)
        tx = x + w / 2
        svg.rect(tx - tw / 2 - 8, by - 2, tw + 16, bw + 8 if T["double"] else bw + 4, bg)
        svg.text(tx, by + bw / 2 - size / 2 - 1, title, size=size, anchor="middle")


# --------------------------------------------------------------------------- stats
QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100,
                 orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes { stargazerCount }
    }
  }
}
"""

YEAR_FIELD = (
    'y{year}: contributionsCollection(from: "{start}", to: "{end}") {{ '
    "totalCommitContributions totalPullRequestContributions totalIssueContributions "
    "contributionCalendar {{ totalContributions }} }}"
)


def graphql(token: str, query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-generator"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        payload = json.load(res)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]


def fetch_alltime(login: str, token: str, created: dt.datetime) -> dict:
    """All-time contribution totals since the account was created.

    contributionsCollection spans at most one year, so query one alias per calendar year.
    """
    now = dt.datetime.now(dt.timezone.utc)
    fields = []
    for year in range(created.year, now.year + 1):
        start = max(created, dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc))
        end = min(now, dt.datetime(year, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc))
        fields.append(YEAR_FIELD.format(year=year, start=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                        end=end.strftime("%Y-%m-%dT%H:%M:%SZ")))
    query = f"query($login: String!) {{ user(login: $login) {{ {' '.join(fields)} }} }}"
    years = graphql(token, query, {"login": login})["user"].values()
    return {
        "contributions": sum(y["contributionCalendar"]["totalContributions"] for y in years),
        "commits": sum(y["totalCommitContributions"] for y in years),
        "prs": sum(y["totalPullRequestContributions"] for y in years),
        "issues": sum(y["totalIssueContributions"] for y in years),
    }


def fetch_stats(login: str, token: str) -> dict:
    u = graphql(token, QUERY, {"login": login})["user"]
    created = dt.datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
    return {
        **fetch_alltime(login, token, created),
        "repos": u["repositories"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
    }


DUMMY_STATS = {
    "contributions": 842, "commits": 654, "prs": 48, "issues": 21,
    "repos": 24, "stars": 37, "followers": 15,
}


def level_threshold(n: int, base: float, exponent: float) -> int:
    """Cumulative contributions required to reach LV n: base * (n - 1) ** exponent."""
    return round(base * (n - 1) ** exponent)


def level_of(contributions: int, cfg: dict) -> int:
    lv_cfg = cfg.get("level", {})
    base = float(lv_cfg.get("base", 10))
    exponent = float(lv_cfg.get("exponent", 2))
    max_lv = int(lv_cfg.get("max", 99))
    lv = 1
    while lv < max_lv and contributions >= level_threshold(lv + 1, base, exponent):
        lv += 1
    return lv


# --------------------------------------------------------------------------- header
def character(cfg: dict) -> tuple[list[str], list[str]]:
    name = cfg.get("character", "bear")
    if name not in sprites.CHARACTERS:
        sys.exit(f"unknown character {name!r}; choose from {', '.join(sprites.CHARACTERS)}")
    return sprites.CHARACTERS[name]


def char_px(grid: list[str]) -> int:
    """Pixel size that keeps characters roughly 64-72px wide regardless of grid size."""
    return max(2, 72 // len(grid[0]))


def build_header(font: Font, cfg: dict) -> Svg:
    W, H = 800, 320
    svg = Svg(font, W, H, f"{cfg['name']} header")
    scene_h = 214

    # sky bands with dithered edges
    for y0, y1, color in T["sky"]:
        svg.rect(0, y0, W, y1 - y0, color)
    g0, g1, g2 = T["grass"]
    defs = "".join(
        f'<pattern id="d{i}" width="8" height="8" patternUnits="userSpaceOnUse">'
        f'<rect width="4" height="4" fill="{c}"/><rect x="4" y="4" width="4" height="4" fill="{c}"/></pattern>'
        for i, (_, c) in enumerate(T["dither"])
    )
    svg.add(
        f'<defs>{defs}<pattern id="grass" width="32" height="16" patternUnits="userSpaceOnUse">'
        f'<rect width="32" height="16" fill="{g0}"/>'
        f'<rect x="4" y="4" width="4" height="4" fill="{g1}"/>'
        f'<rect x="20" y="10" width="4" height="4" fill="{g1}"/>'
        f'<rect x="12" y="12" width="4" height="4" fill="{g2}"/>'
        f'<rect x="28" y="2" width="4" height="4" fill="{g2}"/></pattern></defs>'
    )
    for i, (y, _) in enumerate(T["dither"]):
        svg.rect(0, y, W, 8, f"url(#d{i})")

    # clouds drifting (two copies for a seamless loop)
    clouds = [(60, 10, 4), (330, 26, 3), (560, 6, 4), (720, 30, 3)]
    cloud_parts = "".join(sprite(sprites.CLOUD, x + off, y, px) for off in (0, W) for x, y, px in clouds)
    svg.add(f'<g class="clouds">{cloud_parts}</g>')
    svg.css.append(".clouds{animation:drift 60s linear infinite}"
                   f"@keyframes drift{{to{{transform:translateX(-{W}px)}}}}")

    # mountains (stair-stepped)
    def mountain(cx, base, height, step, color, cap=None):
        rows = height // step
        for i in range(rows):
            half = (rows - i) * step
            y = base - (i + 1) * step
            svg.rect(cx - half, y, half * 2, step, color)
            if cap and i >= rows - 3:
                svg.rect(cx - half, y, half * 2, step, cap)

    for cx, h in ((90, 72), (260, 96), (470, 64), (640, 104), (790, 60)):
        mountain(cx, 150, h, 8, T["mountain"], T["cap"])
    for cx, h in ((0, 40), (180, 32), (380, 44), (560, 28), (740, 36)):
        mountain(cx, 150, h, 4, T["hill"])

    # ground
    svg.rect(0, 150, W, scene_h - 150, "url(#grass)")
    svg.rect(0, 150, W, 4, T["horizon"])
    for tx in (40, 700):
        svg.add(sprite(sprites.TREE, tx, 112, 4))

    # title logo
    title = cfg.get("title", "")
    if title:
        svg.text(W / 2 + 4, 26, title, size=48, fill=T["title_shadow"], anchor="middle")
        svg.text(W / 2, 22, title, size=48, fill=T["title"], anchor="middle",
                 extra=f' stroke="{T["title_stroke"]}" stroke-width="2" paint-order="stroke"')

    # hero (walk cycle) and monster (hop)
    fa, fb = character(cfg)
    px = char_px(fa)
    top = 204 - len(fa) * px
    svg.add(f'<g class="hero">{sprite(fa, 250, top, px, "fa")}{sprite(fb, 250, top, px, "fb")}</g>')
    ea, eb = sprites.ENEMIES[cfg.get("enemy", "slime")]
    svg.add(f'<g class="enemy">{sprite(ea, 486, 138, 4, "fa")}{sprite(eb, 486, 138, 4, "fb")}</g>')
    svg.css.append(
        ".fa{animation:fa .8s steps(1,end) infinite}.fb{opacity:0;animation:fb .8s steps(1,end) infinite}"
        "@keyframes fa{0%{opacity:1}50%{opacity:0}}@keyframes fb{0%{opacity:0}50%{opacity:1}}"
        ".hero{animation:walk 4s steps(1,end) infinite}"
        "@keyframes walk{0%{transform:translateX(0)}25%{transform:translateX(16px)}"
        "50%{transform:translateX(32px)}75%{transform:translateX(16px)}}"
    )

    # message window with typewriter lines
    wy = scene_h - 4
    window(svg, 8, wy, W - 16, H - wy - 4)
    size, line_h, cycle = 22, 34, 10
    lines = cfg.get("messages", [])[:2]
    hold = 1.0  # seconds the full text stays visible at the start of each loop
    t = hold
    for i, line in enumerate(lines):
        top = wy + 22 + i * line_h
        x0 = 40
        tw = svg.text(x0, top, line, size=size)
        cw, ch = tw + 8, size + 6
        svg.add(f'<clipPath id="c{i}"><rect x="{x0 - 2}" y="{top - 2}" width="{cw:.0f}" height="{ch}"/></clipPath>')
        svg.add(f'<g clip-path="url(#c{i})"><rect x="{x0 - 2}" y="{top - 2}" width="{cw:.0f}" '
                f'height="{ch}" fill="{T["bg"]}" class="tw{i}"/></g>')
        # One keyframe per character so mixed full/half-width text is revealed glyph by glyph.
        # The loop starts with the full text shown for `hold` seconds, so renderers that freeze
        # on an early frame (static thumbnails, headless <img> screenshots) still show it.
        frames = [f"0%{{transform:translateX({cw:.0f}px)}}",
                  f"{hold / cycle * 100:.2f}%{{transform:translateX(0)}}"]
        acc = 2.0
        for ch_ in line:
            t += 0.08 if ch_ != " " else 0.0
            acc += font.width(ch_, size)
            frames.append(f"{t / cycle * 100:.2f}%{{transform:translateX({acc:.1f}px)}}")
        frames.append(f"100%{{transform:translateX({cw:.0f}px)}}")
        t += 0.5
        svg.css.append(
            f".tw{i}{{transform:translateX({cw:.0f}px);"
            f"animation:tw{i} {cycle}s step-end infinite}}"
            f"@keyframes tw{i}{{{''.join(frames)}}}"
        )
    svg.add(cursor_down(W - 52, H - (36 if T["double"] else 26), cls="blink"))
    svg.css.append(".blink{animation:blink 1s steps(1,end) infinite}"
                   "@keyframes blink{50%{opacity:0}}")
    return svg


# --------------------------------------------------------------------------- status
def build_status(font: Font, cfg: dict, st: dict, H: int) -> Svg:
    W = 400
    svg = Svg(font, W, H, f"{cfg['name']} status")
    window(svg, 0, 0, W, H, title=cfg.get("status_title", cfg["name"]))
    size = 20
    x0, xr = 28, W - 28

    svg.text(x0, 34, cfg.get("job", ""), size=size, fill=T["accent"])

    # hero portrait (bobbing)
    _, portrait = character(cfg)
    px = char_px(portrait)
    svg.add(f'<g class="bob">{sprite(portrait, xr - len(portrait[0]) * px, 58, px)}</g>')
    svg.css.append(".bob{animation:bob 1.2s steps(1,end) infinite}"
                   "@keyframes bob{50%{transform:translateY(-4px)}}")

    # one label/value column (classic RPG status layout); values share one right edge
    vx = x0 + 248  # left of the portrait (starts at ~x=300)
    rows_top = [
        ("れべる", level_of(st["contributions"], cfg)),
        ("こんとりびゅーしょん", st["contributions"]),
    ]
    rows_bottom = [
        ("こみっと", st["commits"]),
        ("ぷるりくえすと", st["prs"]),
        ("いしゅー", st["issues"]),
        ("りぽじとり", st["repos"]),
        ("すたー", st["stars"]),
        ("ふぉろわー", st["followers"]),
    ]
    for i, (label, val) in enumerate(rows_top):
        svg.text(x0, 70 + i * 34, label, size=18)
        svg.text(vx, 70 + i * 34, str(val), size=18, anchor="end")
    y = 160
    svg.rect(x0 - 4, y - 8, W - 2 * x0 + 8, 2, T["dim"])
    for i, (label, val) in enumerate(rows_bottom):
        svg.text(x0, y + i * 30, label, size=18)
        svg.text(vx, y + i * 30, str(val), size=18, anchor="end")
    return svg


# --------------------------------------------------------------------------- skills
def build_skills(font: Font, cfg: dict, H: int) -> Svg:
    W = 400
    svg = Svg(font, W, H, f"{cfg['name']} skills")
    window(svg, 0, 0, W, H, title=cfg.get("skills_title", "じゅもん"))
    skills = cfg.get("skills", [])[:8]
    x0, top0 = 44, 36
    row_h = min(44, (H - top0 - 24) // max(1, len(skills)))
    seg, gap = 14, 4
    gw = 5 * seg + 4 * gap
    gx = W - 28 - gw
    for i, sk in enumerate(skills):
        top = top0 + i * row_h
        name, found = readings.to_kana(sk["name"], sk.get("kana"))
        if not found:
            print(f"warning: no reading for skill {sk['name']!r}; add it to scripts/readings.py "
                  "or set kana = \"...\" in profile.toml", file=sys.stderr)
        # shrink long names so they never run into the gauge
        size = 20
        avail = gx - 12 - x0
        if font.width(name, size) > avail:
            size = max(12, int(size * avail / font.width(name, size)))
        svg.text(x0, top + (20 - size) / 2, name, size=size)
        lv = int(sk.get("level", 3))
        for j in range(5):
            svg.rect(gx + j * (seg + gap), top + 4, seg, seg, T["fill"] if j < lv else T["dim"])
    if skills:
        n = len(skills)
        frames = "".join(
            f"{i / n * 100:.2f}%{{transform:translateY({i * row_h}px)}}" for i in range(n)
        )
        svg.add(cursor_right(22, top0 + 4, cls="cur"))
        svg.css.append(f".cur{{animation:cur {n * 1.2:.1f}s steps(1,end) infinite}}"
                       f"@keyframes cur{{{frames}}}")
    return svg


def skills_height(cfg: dict) -> int:
    return max(360, 32 + min(len(cfg.get("skills", [])), 8) * 36 + 24)


# --------------------------------------------------------------------------- buttons / footer
def slug(label: str, index: int) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return s or f"link{index}"


def build_button(font: Font, label: str) -> Svg:
    size = 20
    W = int(max(150, font.width(label, size) + 72))
    H = 64 if T["double"] else 56
    svg = Svg(font, W, H, label)
    window(svg, 0, 0, W, H)
    svg.add(cursor_right(22, H / 2 - 7, cls="blink"))
    svg.css.append(".blink{animation:blink 1s steps(1,end) infinite}"
                   "@keyframes blink{50%{opacity:0}}")
    svg.text(44, H / 2 - size / 2, label, size=size)
    return svg


# --------------------------------------------------------------------------- readme
def update_readme(cfg: dict, buttons: list[tuple[str, str, str]]) -> None:
    links = "\n".join(
        f'  <a href="{escape(url)}"><img src="dist/{fname}" height="48" alt="{escape(label)}"></a>'
        for label, url, fname in buttons
    )
    block = f"<!-- COMMANDS:START -->\n<p align=\"center\">\n{links}\n</p>\n<!-- COMMANDS:END -->"
    text = README.read_text(encoding="utf-8")
    new = re.sub(r"<!-- COMMANDS:START -->.*?<!-- COMMANDS:END -->", block, text, flags=re.S)
    if new != text:
        README.write_text(new, encoding="utf-8")


# --------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="use dummy stats")
    mode.add_argument("--live", action="store_true", help="require GITHUB_TOKEN and fetch real stats")
    ap.add_argument("--theme", choices=sorted(THEMES), help="override `theme` in profile.toml")
    ap.add_argument("--out", type=Path, help="output dir (default: dist/; README is not updated)")
    args = ap.parse_args()

    cfg = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    token = os.environ.get("GITHUB_TOKEN")
    if args.live and not token:
        sys.exit("--live requires GITHUB_TOKEN")
    if args.offline or not token:
        if not args.offline:
            print("GITHUB_TOKEN not set; using dummy stats", file=sys.stderr)
        stats = DUMMY_STATS
    else:
        stats = fetch_stats(cfg["github"], token)

    set_theme(args.theme or cfg.get("theme", "mono"))
    font = Font(FONT_PATH)
    out = args.out or DIST
    out.mkdir(parents=True, exist_ok=True)
    H = skills_height(cfg)
    outputs = {
        "header.svg": build_header(font, cfg),
        "status.svg": build_status(font, cfg, stats, H),
        "skills.svg": build_skills(font, cfg, H),
    }
    buttons = []
    for i, link in enumerate(cfg.get("links", [])):
        fname = f"cmd-{slug(link['label'], i)}.svg"
        outputs[fname] = build_button(font, link["label"])
        buttons.append((link["label"], link["url"], fname))

    for old in out.glob("*.svg"):  # drop outputs no longer generated (removed links etc.)
        if old.name not in outputs:
            old.unlink()
    for name, svg in outputs.items():
        (out / name).write_text(svg.render(), encoding="utf-8")
        print(f"wrote {out / name} ({(out / name).stat().st_size / 1024:.1f} KB)")
    if out == DIST:
        update_readme(cfg, buttons)


if __name__ == "__main__":
    main()
