"""Hiragana readings for technology names shown in the skills window.

Lookup is case-insensitive. Prefer the official Japanese reading; otherwise the common one.
Skills from any source (profile.toml, resume repository, GitHub language stats) go through
`to_kana()`. A per-skill `kana = "..."` in profile.toml overrides this table.
"""

READINGS = {
    # languages
    "javascript": "じゃばすくりぷと",
    "typescript": "たいぷすくりぷと",
    "python": "ぱいそん",
    "go": "ごー",
    "rust": "らすと",
    "java": "じゃば",
    "kotlin": "ことりん",
    "swift": "すいふと",
    "objective-c": "おぶじぇくてぃぶしー",
    "c": "しー",
    "c++": "しーぷらすぷらす",
    "c#": "しーしゃーぷ",
    "ruby": "るびー",
    "php": "ぴーえいちぴー",
    "perl": "ぱーる",
    "dart": "だーと",
    "scala": "すから",
    "haskell": "はすける",
    "elixir": "えりくさー",
    "lua": "るあ",
    "r": "あーる",
    "sql": "えすきゅーえる",
    "shell": "しぇる",
    "bash": "ばっしゅ",
    "powershell": "ぱわーしぇる",
    "html": "えいちてぃーえむえる",
    "css": "しーえすえす",
    "scss": "えすしーえすえす",
    "hcl": "えいちしーえる",
    "dockerfile": "どっかーふぁいる",
    "makefile": "めいくふぁいる",
    "jupyter notebook": "じゅぴたーのーとぶっく",
    "graphql": "ぐらふきゅーえる",
    # frameworks / libraries
    "react": "りあくと",
    "vue": "びゅー",
    "vue.js": "びゅー",
    "angular": "あんぎゅらー",
    "svelte": "すべると",
    "next.js": "ねくすとじぇーえす",
    "nuxt": "なくすと",
    "node.js": "のーどじぇーえす",
    "tailwind css": "ているうぃんど",
    "django": "じゃんご",
    "flask": "ふらすく",
    "fastapi": "ふぁすとえーぴーあい",
    "ruby on rails": "るびーおんれいるず",
    "rails": "れいるず",
    "laravel": "られべる",
    "spring boot": "すぷりんぐぶーと",
    "flutter": "ふらったー",
    "unity": "ゆにてぃ",
    # infrastructure / tools
    "docker": "どっかー",
    "kubernetes": "くばねてぃす",
    "terraform": "てらふぉーむ",
    "aws": "えーだぶりゅーえす",
    "gcp": "じーしーぴー",
    "google cloud": "ぐーぐるくらうど",
    "azure": "あじゅーる",
    "firebase": "ふぁいあべーす",
    "linux": "りなっくす",
    "git": "ぎっと",
    "github": "ぎっとはぶ",
    "github actions": "ぎっとはぶあくしょんず",
    "mysql": "まいえすきゅーえる",
    "postgresql": "ぽすとぐれすきゅーえる",
    "redis": "れでぃす",
    "mongodb": "もんごでぃーびー",
}


def to_kana(name: str, override: str | None = None) -> tuple[str, bool]:
    """Return (display name, found). Falls back to the original name when unknown."""
    if override:
        return override, True
    kana = READINGS.get(name.strip().lower())
    return (kana, True) if kana else (name, False)
