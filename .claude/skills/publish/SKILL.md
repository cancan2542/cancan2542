---
name: publish
description: Commit the profile changes, push to main, and watch the GitHub Actions run until the profile is updated.
disable-model-invocation: true
allowed-tools: Bash(git status*) Bash(git diff*) Bash(git add *) Bash(git commit *) Bash(git push origin main) Bash(gh run *)
---

# Publish the profile

1. Run the `preview` skill steps first if SVGs or scripts changed since the last preview.
2. `git status` / `git diff --stat` — confirm only intended files changed
   (no temp files, no `__pycache__`, no `.env`).
3. Commit with a conventional message (`feat:`, `fix:`, `chore:`), then `git push origin main`.
4. `gh run list --workflow update.yml --limit 1` and `gh run watch <id> --exit-status`.
5. On failure: `gh run view <id> --log-failed`, fix locally, re-run preview, and ask the user before pushing again.
6. Report the run result and the profile URL https://github.com/cancan2542.
