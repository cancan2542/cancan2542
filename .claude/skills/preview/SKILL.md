---
name: preview
description: Regenerate the profile SVGs in Docker and render preview screenshots to visually verify layout and animations. Use after changing profile.toml, scripts/, or sprites, or when the user asks to see how the profile looks.
argument-hint: "[ms ...]"
allowed-tools: Bash(docker compose run --rm generate*) Bash(docker compose run --rm preview*) Bash(docker compose build*) Bash(mktemp -d*)
---

# Preview the profile

1. Regenerate with dummy stats:
   `docker compose run --rm generate`
   - Fix any `warning: glyphs missing in font` before continuing.
2. Render screenshots into a temp dir outside the repo:
   `OUT=$(mktemp -d) && PREVIEW_OUT=$OUT docker compose run --rm preview $ARGUMENTS && echo $OUT`
   - No arguments → header frames at 1500ms and 4000ms. Pass ms values to inspect other frames.
3. Read `$OUT/overview.png` (README layout via `<img>`, animations frozen at t=0)
   and each `$OUT/header-<ms>.png` (animations seeked).
4. Check: text not clipped by window borders, title labels sit on the top border,
   pixel art aligned, both columns (status / skills) the same height, file sizes reported by
   generate are under ~100KB.
5. Report what you saw. Do not commit or push as part of this skill.
