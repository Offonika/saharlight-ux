# filename: scripts/quick_shas_and_diffs.sh
#!/usr/bin/env bash
set -euo pipefail
git fetch --all --prune
echo "HEAD main:    $(git rev-parse origin/main)"
echo "HEAD lovable: $(git rev-parse origin/lovable)"
echo
echo "[src]"
git diff --name-status origin/main...origin/lovable -- services/webapp/ui/src || true
echo
echo "[public]"
git diff --name-status origin/main...origin/lovable -- services/webapp/ui/public || true
echo
echo "[ts-sdk]"
git diff --name-status origin/main...origin/lovable -- libs/ts-sdk || true
echo
echo "[configs if touched]"
for f in services/webapp/ui/package.json services/webapp/ui/vite.config.ts services/webapp/ui/tailwind.config.ts services/webapp/ui/index.html; do
  if git diff --name-only origin/main...origin/lovable -- "$f" | grep -q .; then
    echo "-- $f"
    git diff --unified=1 origin/main...origin/lovable -- "$f" || true
    echo
  fi
done
