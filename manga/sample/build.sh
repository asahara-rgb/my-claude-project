#!/usr/bin/env bash
# サンプル短編を HTML → PNG → EPUB まで一括生成する。manga/ で実行。
set -euo pipefail
cd "$(dirname "$0")/.."
node tools/render_pages.mjs sample/src sample/pages
mv sample/pages/cover.png sample/cover.png
python3 tools/check_pages.py --pages sample/pages --cover sample/cover.png
python3 tools/build_epub.py --pages sample/pages --cover sample/cover.png \
  --out dist/sample.epub --title "ねこと電子書籍" --author "サンプル著者"
echo "→ dist/sample.epub を Kindle Previewer で開いて確認"
