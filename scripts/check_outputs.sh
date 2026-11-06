#!/bin/sh
# Security check for generated / committed files. POSIX sh + grep only (runs on host, in hooks and in CI).
#   - Token leaks in any file (GitHub tokens, private keys, the literal $GITHUB_TOKEN / $PROFILE_TOKEN value)
#   - Unsafe SVG content in *.svg (scripts, event handlers, foreignObject, external URLs)
# Usage: sh scripts/check_outputs.sh <file|dir> ...   → exit 0 = clean, exit 2 = findings (on stderr)
# Matched secrets are never printed, only file:line and the kind of finding.
set -u

found=0
report() { echo "security: $1" >&2; found=1; }

# Print line numbers (only) of lines matching an extended regex.
lines() { grep -naiE -e "$1" "$2" 2>/dev/null | cut -d: -f1 | tr '\n' ' '; }

check_file() {
  f=$1
  for re in 'gh[pousr]_[A-Za-z0-9]{36,}' 'github_pat_[A-Za-z0-9_]{22,}' '-----BEGIN [A-Z ]*PRIVATE KEY'; do
    n=$(LC_ALL=C grep -naE -e "$re" "$f" 2>/dev/null | cut -d: -f1 | tr '\n' ' ')
    [ -n "$n" ] && report "$f: possible secret ($re) at line $n"
  done
  for val in "${GITHUB_TOKEN:-}" "${PROFILE_TOKEN:-}"; do
    if [ "${#val}" -ge 20 ] && LC_ALL=C grep -qaF -e "$val" "$f" 2>/dev/null; then
      report "$f: contains the value of \$GITHUB_TOKEN / \$PROFILE_TOKEN"
    fi
  done

  case $f in
    *.svg|*.SVG) ;;
    *) return ;;
  esac
  # Event handlers need leading whitespace so base64 font data (…on+=) does not match.
  for re in '<script' '<foreignObject' 'javascript:' '@import' '[[:space:]]on[a-z]+[[:space:]]*=' \
            '<(iframe|embed|object)' '(href|src)[[:space:]]*=[[:space:]]*["'"'"']?[[:space:]]*(https?:|//)' \
            'url\([[:space:]]*["'"'"']?[[:space:]]*(https?:|//)'; do
    n=$(lines "$re" "$f")
    [ -n "$n" ] && report "$f: unsafe SVG content ($re) at line $n"
  done
  # Any other absolute URL besides the SVG / XLink namespaces.
  urls=$(LC_ALL=C grep -aoiE 'https?://[^"'"'"' )<>]+' "$f" 2>/dev/null \
    | grep -viE '^http://www\.w3\.org/(2000/svg|1999/xlink)$' | sort -u | head -5 | tr '\n' ' ')
  [ -n "$urls" ] && report "$f: external URL in SVG: $urls"
}

[ $# -gt 0 ] || { echo "usage: $0 <file|dir> ..." >&2; exit 64; }
for p in "$@"; do
  if [ -d "$p" ]; then
    for f in $(find "$p" -type f ! -path '*/.git/*' | sort); do check_file "$f"; done
  elif [ -f "$p" ]; then
    check_file "$p"
  fi
done

[ "$found" -eq 0 ] || exit 2
exit 0
