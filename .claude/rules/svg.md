---
paths:
  - "scripts/**"
  - "profile.toml"
---

# SVG generator rules

## Theme
- 色は必ずテーマ `T[...]`（`THEMES` / `four_tone()`）経由で指定し、描画関数に色を直書きしない。新しい色の役割が要るときは全テーマにキーを追加する
- スプライトの色は `T["sprite"]` で4階調へ置き換わる。`sprites.COLORS` に色を足したら `four_tone()` の対応表にも追加する
- テーマ比較は `--theme <name> --out <dir>` でリポジトリ外に出力する（`--out` 指定時は README を更新しない）

## Pixel style
- ルートSVGは `shape-rendering="crispEdges"`。座標・サイズは 2px か 4px の倍数に揃える
- ドット絵は `scripts/sprites.py` の文字グリッドで定義し `sprite()` で描く。色は `COLORS` に追加してから使う（`validate()` が未定義色・行長不一致を検出）
- 窓は必ず `window()` を使う（黒地・白枠・角欠け）。タイトル付きは上枠が下がる点に注意
- テキストは `Svg.text(x, top, ...)`。`top` は em ボックス上端で、ベースラインはフォントメトリクスから算出される
- 文字幅は `Font.width()` を使う（全角/半角混在のため文字数×定数で計算しない）

## Animation
- CSS keyframes を `svg.css` に追加。SMIL や JS は使わない
- 段階的な動きは `steps(1,end)` / `step-end` で8bit感を出す
- 非アニメ時の基本状態で内容が読めること（`prefers-reduced-motion` で全停止される）

## Font / size
- 使用文字は自動で収集・サブセット化される。`warning: glyphs missing in font` が出たら文字を変えるかドット描画にする（例: ▶▼ は `cursor_right()` / `cursor_down()`）
- 1ファイル 100KB 以下を目安。超える場合は文字種やスプライトのrect数を見直す

## Text
- 画面上のラベルはひらがなで統一する（英語・カタカナは浮くため）
- 技術名は取得元（profile.toml / 職務経歴書 / GitHub言語統計）を問わず `readings.to_kana()` を通す。読みは公式の呼称を優先し、なければ一般的な呼称。`warning: no reading for skill` が出たら `scripts/readings.py` に追加する

## Stats
- GraphQL取得は `fetch_stats()`、オフライン用は `DUMMY_STATS`。キーを増やすときは両方を更新する
