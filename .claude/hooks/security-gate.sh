#!/bin/bash
# Claude Code security hook for Bash tool calls. Usage (from .claude/settings.json):
#   PreToolUse  → security-gate.sh pre    (deny / ask before builds, commits, pushes)
#   PostToolUse → security-gate.sh post   (feedback after generate / build)
# Heavy checks run in containers (compose services `trivy`, `audit`); nothing is installed on the host.
# If Docker or the network is unavailable, the check is reported as "skipped" instead of passing silently.
# No `set -u`: macOS /bin/bash 3.2 treats empty arrays as unbound.

phase=${1:-}
cmd=$(jq -r '.tool_input.command // empty' 2>/dev/null)
[ -n "$cmd" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0

has() { printf '%s' "$cmd" | grep -qE -- "$1"; }
RE_BUILD='docker[[:space:]]+(compose[[:space:]]+([^|;&]*[[:space:]])?|buildx[[:space:]]+)?build([[:space:]]|$)'
RE_GENERATE='docker[[:space:]]+compose[[:space:]]+run[^|;&]*[[:space:]]generate([[:space:]]|$)'
RE_COMMIT='git[[:space:]]+([^|;&]*[[:space:]])?commit([[:space:]]|$)'
RE_PUSH='git[[:space:]]+([^|;&]*[[:space:]])?push([[:space:]]|$)'
BUILD_INPUTS=(Dockerfile docker requirements.txt compose.yaml .dockerignore)

problems=()   # → deny (pre) / block (post)
warnings=()   # → shown to the user, does not block
asks=()       # → ask (pre only)

tmp=""
cleanup() { [ -n "$tmp" ] && rm -rf "$tmp"; }
trap cleanup EXIT
mktmp() { [ -n "$tmp" ] || tmp=$(mktemp -d "${TMPDIR:-/tmp}/security-gate.XXXXXX"); }

docker_ok() { docker info >/dev/null 2>&1; }

# run_trivy <docker-run-args...> -- <trivy-args...>
#   → $trivy_out = one line per finding (secret values are never printed), $trivy_err = last stderr line
#   → return 0 = clean, 5 = findings, other = trivy/docker error
run_trivy() {
  local dargs=() json rc
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do dargs+=("$1"); shift; done
  shift
  mktmp
  json=$(docker compose run --rm -T "${dargs[@]}" trivy --quiet "$@" --format json --exit-code 5 2>"$tmp/trivy.err"); rc=$?
  trivy_err=$(grep -v '^[[:space:]]*$' "$tmp/trivy.err" | tail -1)
  trivy_out=$(printf '%s' "$json" | jq -r '.Results[]? | .Target as $t |
      ((.Misconfigurations // [])[] | "\($t): \(.ID) (\(.Severity)) \(.Title)"),
      ((.Secrets // [])[] | "\($t):\(.StartLine): \(.RuleID) (\(.Severity)) \(.Title)"),
      ((.Vulnerabilities // [])[] | "\($t): \(.PkgName) \(.InstalledVersion) -> \(.FixedVersion) \(.VulnerabilityID) (\(.Severity))")' \
    2>/dev/null | sort -u | head -20)
  return $rc
}

check_outputs() {  # <label> <dir to run in> <paths...>
  local label=$1 dir=$2 out script="$PWD/scripts/check_outputs.sh"; shift 2
  if ! out=$(cd "$dir" && sh "$script" "$@" 2>&1); then
    problems+=("[$label] $out")
  fi
}

trivy_config() {
  docker_ok || { warnings+=("trivy config: skipped (docker unavailable)"); return; }
  run_trivy -- config --severity HIGH,CRITICAL --skip-dirs /src/dist,/src/assets /src
  case $? in
    0) ;;
    5) problems+=("[trivy config] HIGH/CRITICAL misconfiguration:
$trivy_out") ;;
    *) warnings+=("trivy config: skipped (error: $trivy_err)") ;;
  esac
}

trivy_secret() {  # <host dir to scan>
  docker_ok || { warnings+=("trivy secret: skipped (docker unavailable)"); return; }
  run_trivy -v "$1:/scan:ro" -- fs --scanners secret --skip-dirs /scan/assets /scan
  case $? in
    0) ;;
    5) problems+=("[trivy secret] secrets found in the commit:
$trivy_out") ;;
    *) warnings+=("trivy secret: skipped (error: $trivy_err)") ;;
  esac
}

# --- PreToolUse -----------------------------------------------------------------------------------
pre_build() {
  local changed
  changed=$(git status --porcelain -- "${BUILD_INPUTS[@]}" 2>/dev/null)
  if [ -n "$changed" ]; then
    asks+=("Build inputs differ from HEAD (review before building):
$changed
$(git diff --stat HEAD -- "${BUILD_INPUTS[@]}" 2>/dev/null | tail -5)")
  fi
  trivy_config
}

pre_commit() {
  mktmp
  local snap="$tmp/index"
  mkdir -p "$snap"
  git checkout-index -a --prefix="$snap/" 2>/dev/null
  # `git commit -a` / `--all` stages tracked changes at commit time: include their working-tree copies.
  if printf '%s' "$cmd" | grep -qE -- '(^|[[:space:]])(-[a-zA-Z]*a[a-zA-Z]*|--all)([[:space:]]|$)'; then
    git diff --name-only -z | while IFS= read -r -d '' f; do
      [ -f "$f" ] && mkdir -p "$snap/$(dirname "$f")" && cp "$f" "$snap/$f"
    done
  fi
  check_outputs "commit" "$snap" .
  trivy_secret "$snap"
}

pre_push() {
  local range
  if git rev-parse -q --verify '@{u}' >/dev/null 2>&1; then range='@{u}..HEAD'
  elif git rev-parse -q --verify origin/main >/dev/null 2>&1; then range='origin/main..HEAD'
  else range='HEAD'; fi
  mktmp
  git log -p --no-color "$range" -- 2>/dev/null | grep -E '^\+' > "$tmp/push.diff"
  check_outputs "push $range" "$tmp" push.diff
}

# --- PostToolUse ----------------------------------------------------------------------------------
post_generate() {
  check_outputs "generate" . dist README.md
}

post_build() {
  docker_ok || { warnings+=("pip-audit / trivy image: skipped (docker unavailable)"); return; }
  mktmp
  local out rc img

  # pip-audit against the exact packages installed in the generator image
  if docker image inspect profile-generator >/dev/null 2>&1; then
    # pip is removed from the image, so list installed distributions via importlib.metadata
    docker run --rm --entrypoint python profile-generator -c \
      'import importlib.metadata as m; print("\n".join(sorted({f"{d.name}=={d.version}" for d in m.distributions()})))' \
      > "$tmp/req.txt" 2>/dev/null
    out=$(docker compose run --rm -T --build -v "$tmp:/scan:ro" audit \
          -r /scan/req.txt --no-deps --disable-pip 2>&1); rc=$?
    if printf '%s' "$out" | grep -q 'No known vulnerabilities found'; then :
    elif printf '%s' "$out" | grep -qE 'Found [0-9]+ known vulnerabilit'; then
      problems+=("[pip-audit] vulnerable Python packages in profile-generator:
$(printf '%s\n' "$out" | grep -vE '^\s*$' | tail -15)")
    else
      warnings+=("pip-audit: skipped (rc=$rc: $(printf '%s' "$out" | tail -1))")
    fi
  fi

  # Trivy OS/library scan of the built images (via `docker save`, no docker.sock mount)
  for img in profile-generator profile-preview; do
    docker image inspect "$img" >/dev/null 2>&1 || continue
    docker save "$img" -o "$tmp/$img.tar" 2>/dev/null || { warnings+=("trivy image $img: skipped (docker save failed)"); continue; }
    run_trivy -v "$tmp:/scan:ro" -- image --input "/scan/$img.tar" --severity HIGH,CRITICAL --ignore-unfixed
    rc=$?
    rm -f "$tmp/$img.tar"
    case $rc in
      0) ;;
      5) problems+=("[trivy image $img] fixable HIGH/CRITICAL vulnerabilities (rebuild with \`docker compose build --pull --no-cache\` or bump versions):
$trivy_out") ;;
      *) warnings+=("trivy image $img: skipped (error: $trivy_err)") ;;
    esac
  done
}

# --- dispatch -------------------------------------------------------------------------------------
case $phase in
  pre)
    has "$RE_BUILD" && pre_build
    has "$RE_COMMIT" && pre_commit
    has "$RE_PUSH" && pre_push
    ;;
  post)
    has "$RE_GENERATE" && post_generate
    has "$RE_BUILD" && post_build
    ;;
  *) exit 0 ;;
esac

join() { local IFS=$'\n'; printf '%s' "$*"; }
warn_msg=""
[ ${#warnings[@]} -gt 0 ] && warn_msg="security-gate warnings (not verified):
$(join "${warnings[@]}")"

if [ "$phase" = pre ]; then
  if [ ${#problems[@]} -gt 0 ]; then
    jq -n --arg r "security-gate blocked this command:
$(join "${problems[@]}")" --arg w "$warn_msg" \
      '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}} + (if $w != "" then {systemMessage:$w} else {} end)'
  elif [ ${#asks[@]} -gt 0 ]; then
    jq -n --arg r "$(join "${asks[@]}")" --arg w "$warn_msg" \
      '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"ask",permissionDecisionReason:$r}} + (if $w != "" then {systemMessage:$w} else {} end)'
  elif [ -n "$warn_msg" ]; then
    jq -n --arg w "$warn_msg" '{systemMessage:$w}'
  fi
else
  if [ ${#problems[@]} -gt 0 ]; then
    jq -n --arg r "security-gate found problems after this command. Fix them before committing:
$(join "${problems[@]}")" --arg w "$warn_msg" \
      '{decision:"block",reason:$r} + (if $w != "" then {systemMessage:$w} else {} end)'
  elif [ -n "$warn_msg" ]; then
    jq -n --arg w "$warn_msg" '{systemMessage:$w, hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$w}}'
  fi
fi
exit 0
