#!/bin/bash
# 進捗ダッシュボードを最新Gistから再生成する。
# 使い方:  bash _progress/update.sh
set -e
cd "$(dirname "$0")"

echo "▶ 最新Gist(shindanshi-matome notes)を探索..."
GID=$(gh gist list --limit 50 | awk -F'\t' '$2=="shindanshi-matome notes"{print $1"\t"$4}' \
      | sort -k2 -r | head -1 | cut -f1)
if [ -z "$GID" ]; then echo "✗ Gistが見つかりません"; exit 1; fi
echo "  Gist: $GID"

echo "▶ notes.json を取得..."
# 差分用に前回分を退避
[ -f notes.json ] && cp notes.json notes_prev.json
RAW=$(gh api "gists/$GID" --jq '.files["notes.json"].raw_url')
curl -s "$RAW" -o notes.json
echo "  $(wc -c < notes.json) bytes"

echo "▶ ダッシュボード生成（差分も画面と出力に反映）..."
echo ""
UPDATE_TS="$(date +%Y-%m-%dT%H:%M:%S%z)" python3 build_dashboard.py notes.json notes_prev.json
echo ""

echo "▶ 開く"
open -a "Google Chrome" "../学習進捗ダッシュボード.html" 2>/dev/null || true
echo "✓ 完了"
