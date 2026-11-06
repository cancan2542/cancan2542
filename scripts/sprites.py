"""Pixel-art sprites as character grids.

Each character maps to a palette color (see COLORS); "." is transparent.
All rows of a sprite must have the same length.
"""

COLORS = {
    "K": "#000000",  # outline
    "W": "#fcfcfc",  # white
    "S": "#fcbcb0",  # skin
    "B": "#0058f8",  # blue
    "b": "#3cbcfc",  # light blue
    "Y": "#f8b800",  # yellow
    "R": "#d82800",  # red
    "r": "#f87858",  # light red
    "L": "#ac7c00",  # brown
    "G": "#7c7c7c",  # gray
    "g": "#bcbcbc",  # light gray
    "E": "#005800",  # dark green
    "e": "#00a800",  # green
    "f": "#58d854",  # light green
    "N": "#1c2a4a",  # navy (hoodie)
    "n": "#40c8c8",  # teal (hood rim light)
    "T": "#e09850",  # tan (bear fur)
    "t": "#f8d8a8",  # cream (muzzle / inner ear)
}


def mirror(rows: list[str], width: int) -> list[str]:
    """Rows of width/2 are mirrored to full width; full-width rows pass through."""
    return [r + r[::-1] if len(r) == width // 2 else r for r in rows]


# Hooded bear with a laptop (based on the profile icon), 24px wide, two walking frames.
_BEAR_TOP = [
    "..KKKK......",
    ".KTTTTK.KKKK",
    ".KTttTKKNNNN",
    ".KTttTKNNNNN",
    "..KTTKNNNNNN",
    "...KNNNNNNNN",
    "..KnNNNNNNNN",
    "..KnNNKKKKKK",
    ".KnNNKTTTTTT",
    ".KnNKTTTTTTT",
    ".KnNKTTTKTTT",
    ".KnNKTTTKTTT",
    ".KnNKTTTtttt",
    ".KnNKTTtttKK",
    ".KnNKTTttttK",
    "..KnNKTTtttt",
    "..KNNNKKKKKK",
    ".KNNNNNNNNNN",
    ".KNKKKKKKKKK",
    "KTTKbbbbbbbb",
    "KTTKbbbbbbbb",
    ".KKKbbbbbbbb",
    "..KNKKKKKKKK",
    "..KNGGGGGGGG",
    "..KNNNNNNNNN",
]
BEAR_A = mirror(_BEAR_TOP + ["....KTTTK...", "....KKKKK..."], 24)
BEAR_B = mirror(_BEAR_TOP + ["...KTTTK....", "...KKKKK...."], 24)

# Hero (coder-adventurer with a hood), 16px wide, two walking frames.
_HERO_TOP = [
    "......KKKK......",
    "....KKBBBBKK....",
    "...KBBBBBBBBK...",
    "..KBBbbBBBBBBK..",
    "..KBbBBBBBBBBK..",
    "..KKKKKKKKKKKK..",
    "..KSSSSSSSSSSK..",
    "..KSSKSSSSKSSK..",
    "..KSSKSSSSKSSK..",
    "...KSSSrrSSSK...",
    "....KKKKKKKK....",
    "..KKRYYYYYYRKK..",
    ".KSKRYYYYYYRKSK.",
    ".KSKRYYKKYYRKSK.",
    "..KKRYYYYYYRKK..",
    "...KKLLLLLLKK...",
]
HERO_A = _HERO_TOP + [
    "....KBBKKBBK....",
    "....KBBKKBBK....",
    "...KLLLK.KLLLK..",
    "...KKKKK.KKKKK..",
]
HERO_B = _HERO_TOP + [
    "....KBBKKBBK....",
    "...KBBK..KBBK...",
    "..KLLLK..KLLLK..",
    "..KKKKK..KKKKK..",
]

# A wild "bug" monster (beetle with antennae).
BUG_A = [
    "..K..........K..",
    "...K........K...",
    "....K......K....",
    ".....KKKKKK.....",
    "...KKRRRRRRKK...",
    "..KRRrRRRRrRRK..",
    "..KRWWRRRRWWRK..",
    ".KRRWKRRRRWKRRK.",
    ".KRRRRRRRRRRRRK.",
    "KKRRRRRKKRRRRRKK",
    "K.KRRrRKKRrRRK.K",
    "..KRRRRKKRRRRK..",
    "...KRRRKKRRRK...",
    "..K.KKKKKKKK.K..",
    ".K..K......K..K.",
    "K...K......K...K",
]
BUG_B = [
    "................",
    ".K............K.",
    "..K..........K..",
    "...KKKKKKKKKK...",
    "..KKRRRRRRRRKK..",
    "..KRRrRRRRrRRK..",
    "..KRWWRRRRWWRK..",
    ".KRRWKRRRRWKRRK.",
    ".KRRRRRRRRRRRRK.",
    "KKRRRRRKKRRRRRKK",
    "K.KRRrRKKRrRRK.K",
    "..KRRRRKKRRRRK..",
    "...KRRRKKRRRK...",
    "...KKKKKKKKKK...",
    "..K.K......K.K..",
    ".K..K......K..K.",
]

# A wild slime: round dome blob with a shine; frame B is squashed for a bounce.
SLIME_A = [
    "................",
    "................",
    "................",
    "......KKKK......",
    "....KKeeeeKK....",
    "...KeWWeeeeeK...",
    "..KeWWeeeeeeeK..",
    "..KeWeeeeeeeeK..",
    ".KeeeKeeeeKeeeK.",
    ".KeeeKeeeeKeeeK.",
    ".KeeeeeeeeeeeeK.",
    ".KeeeeeKKeeeeeK.",
    "KEeeeeeeeeeeeeEK",
    "KEEeeeeeeeeeeEEK",
    ".KEEEEEEEEEEEEK.",
    "..KKKKKKKKKKKK..",
]
SLIME_B = [
    "................",
    "................",
    "................",
    "................",
    "................",
    ".....KKKKKK.....",
    "...KKeeeeeeKK...",
    "..KeWWeeeeeeeK..",
    ".KeWWeeeeeeeeeK.",
    ".KeWeKeeeeKeeeK.",
    ".KeeeKeeeeKeeeK.",
    "KeeeeeeeeeeeeeeK",
    "KeeeeeeKKeeeeeeK",
    "KEEeeeeeeeeeeEEK",
    "KEEEEEEEEEEEEEEK",
    ".KKKKKKKKKKKKKK.",
]

CLOUD = [
    "......WWWW..........",
    "....WWWWWWWW..WWW...",
    "..WWWWWWWWWWWWWWWW..",
    ".WWWWWWWWWWWWWWWWWW.",
    "WWWWWWWWWWWWWWWWWWWW",
    ".gWWWWWWWWWWWWWWWWg.",
    "..gggggggggggggggg..",
]

TREE = [
    "....KKKK....",
    "..KKeeffKK..",
    ".KeeeeeffeK.",
    ".KeEeeeeeeK.",
    "KeeeeeEeeefK",
    "KeEeeeeeeeeK",
    ".KeeeEeeEeK.",
    "..KKeeeeKK..",
    "....KLLK....",
    "....KLLK....",
    "...KKKKKK...",
]


# Selectable player characters: name -> (walk frame A, walk frame B / portrait)
CHARACTERS = {
    "bear": (BEAR_A, BEAR_B),
    "hero": (HERO_A, HERO_B),
}

# Selectable enemies in the header: name -> (frame A, frame B)
ENEMIES = {
    "slime": (SLIME_A, SLIME_B),
    "bug": (BUG_A, BUG_B),
}


def validate():
    for name, grid in list(globals().items()):
        if isinstance(grid, list) and grid and isinstance(grid[0], str):
            widths = {len(r) for r in grid}
            assert len(widths) == 1, f"{name}: ragged rows {widths}"
            unknown = set("".join(grid)) - set(COLORS) - {"."}
            assert not unknown, f"{name}: unknown colors {unknown}"


validate()
