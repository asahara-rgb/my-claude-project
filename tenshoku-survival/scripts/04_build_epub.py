#!/usr/bin/env python3
"""build/pages/*.jpg から右開き固定レイアウト EPUB を生成する（../manga/tools/build_epub.py を利用）。

  python3 scripts/04_build_epub.py                       # book.json の設定で build/tenshoku-survival.epub
  python3 scripts/04_build_epub.py --cover build/cover.jpg --out build/ep01.epub

book.json（このフォルダ直下）にタイトル・著者・識別子・章（chapters: 各話の開始ページ）を書く。
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER = os.path.join(os.path.dirname(ROOT), "manga", "tools", "build_epub.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default=os.path.join(ROOT, "book.json"))
    ap.add_argument("--pages", default=os.path.join(ROOT, "build", "pages"))
    ap.add_argument("--cover")
    ap.add_argument("--out")
    a = ap.parse_args()
    if not os.path.isfile(BUILDER):
        raise SystemExit(f"EPUB ビルダーが見つかりません: {BUILDER}（manga/ フォルダが必要です）")
    cmd = [sys.executable, BUILDER, "--book", a.book, "--pages", a.pages]
    if a.cover:
        cmd += ["--cover", a.cover]
    if a.out:
        cmd += ["--out", a.out]
    print("$", " ".join(os.path.relpath(c, ROOT) if os.path.isabs(c) else c for c in cmd))
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
