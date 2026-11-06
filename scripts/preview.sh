#!/bin/sh
# Render preview PNGs of dist/*.svg into /out (runs inside the `preview` container).
#   overview.png      … README-like layout using <img> (same constraints as GitHub)
#   header-<ms>.png   … header.svg with all animations seeked to <ms> milliseconds
# Usage (host): docker compose run --rm preview [ms ...]   (default: 1500 4000)
set -eu

OUT=/out
D=/app/dist
TIMES="${*:-1500 4000}"
chrome() {
  chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
    --disable-dev-shm-usage "$@" >/dev/null 2>&1
}

buttons=""
for f in "$D"/cmd-*.svg; do
  [ -e "$f" ] && buttons="$buttons<img src=\"file://$f\" height=\"48\"> "
done

cat > "$OUT/overview.html" <<EOF
<html><body style="background:#0d1117;margin:0;padding:16px;width:868px">
<img src="file://$D/header.svg" width="100%"><br>
<img src="file://$D/status.svg" width="49%"> <img src="file://$D/skills.svg" width="49%">
<p align="center">$buttons</p>
</body></html>
EOF
chrome --window-size=900,1100 --screenshot="$OUT/overview.png" "file://$OUT/overview.html"
echo "overview.png"

for t in $TIMES; do
  {
    echo "<html><body style='margin:0;background:#000'>"
    cat "$D/header.svg"
    echo "<script>document.getAnimations().forEach(a=>{a.pause();a.currentTime=$t})</script></body></html>"
  } > "$OUT/header-$t.html"
  chrome --window-size=800,320 --screenshot="$OUT/header-$t.png" "file://$OUT/header-$t.html"
  echo "header-$t.png"
done
