#!/usr/bin/env python3
"""原稿画像の検品。連番の抜け・サイズ不一致・容量超過・カラーモードを報告する。

  python3 tools/check_pages.py                 # book.json の pages_dir / cover
  python3 tools/check_pages.py --pages sample/pages --cover sample/cover.png

終了コード 0 = 問題なし, 1 = エラーあり（警告のみなら 0）。
"""
import argparse
import os
import sys

from PIL import Image

from common import PAGE_RE, human, list_pages, load_book, resolve

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 650 * 1024 * 1024
COVER_MIN = (625, 1000)
COVER_MAX = 10000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", help="book.json のパス")
    ap.add_argument("--pages")
    ap.add_argument("--cover")
    a = ap.parse_args()
    book = load_book(a.book)
    pages_dir = a.pages or resolve(book, book["pages_dir"])
    cover = a.cover or resolve(book, book["cover"])
    W, H = book["page_width"], book["page_height"]

    errors, warns = [], []
    pages = list_pages(pages_dir)
    if not pages:
        errors.append(f"ページ画像が1枚もありません: {pages_dir}")

    total = 0
    expected = 1
    print(f"{'file':28} {'size':>11} {'mode':>5} {'bytes':>9}  note")
    for p in pages:
        name = os.path.basename(p)
        size = os.path.getsize(p)
        total += size
        note = []
        m = PAGE_RE.match(os.path.splitext(name)[0])
        if not m:
            warns.append(f"{name}: 連番として解釈できない名前（p001.png 形式を推奨）")
        else:
            n1 = int(m.group(1))
            n2 = int(m.group(2)) if m.group(2) else n1
            if n1 != expected:
                errors.append(f"{name}: 連番が飛んでいます（期待 p{expected:03d}）")
            expected = n2 + 1
        try:
            with Image.open(p) as im:
                w, h = im.size
                mode = im.mode
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: 画像として開けません ({e})")
            continue
        if (w, h) == (W, H):
            note.append("single")
        elif (w, h) == (W * 2, H):
            note.append("spread")
        elif w > h:
            warns.append(f"{name}: 横長ですが {W*2}x{H} ではありません → 見開きとして中央配置されます")
            note.append("spread?")
        else:
            warns.append(f"{name}: {w}x{h} は既定 {W}x{H} と異なります（prepare_pages.py で統一できます）")
            note.append("resize")
        if abs(w / h - W / H) > 0.02 and w <= h:
            warns.append(f"{name}: 縦横比 {w/h:.3f} が既定 {W/H:.3f} とずれています（余白または切り抜きが発生）")
        if size > MAX_IMAGE_BYTES:
            errors.append(f"{name}: {human(size)} は 1画像 5MB の上限を超えています")
        if mode in ("RGBA", "LA", "P"):
            warns.append(f"{name}: モード {mode}（透過/パレット）。RGB か L に変換推奨")
        print(f"{name:28} {f'{w}x{h}':>11} {mode:>5} {human(size):>9}  {' '.join(note)}")

    print(f"\n本文 {len(pages)} 枚, 合計 {human(total)}")
    if total > MAX_TOTAL_BYTES:
        errors.append(f"合計 {human(total)} はアップロード上限 650MB を超えています")

    if os.path.isfile(cover):
        with Image.open(cover) as im:
            w, h = im.size
            fmt = im.format
        size = os.path.getsize(cover)
        print(f"表紙 {os.path.basename(cover)}: {w}x{h} {fmt} {human(size)}")
        if fmt not in ("JPEG", "TIFF"):
            warns.append(f"表紙: KDP へ直接アップロードする表紙は JPEG/TIFF 推奨（現在 {fmt}）。EPUB 内の表紙としては PNG でも可")
        if w < COVER_MIN[0] or h < COVER_MIN[1]:
            errors.append(f"表紙: {w}x{h} は最小 625x1000 未満")
        if max(w, h) > COVER_MAX:
            errors.append(f"表紙: 長辺 {max(w,h)} は上限 10000px 超")
        if abs(h / w - 1.6) > 0.05:
            warns.append(f"表紙: 縦横比 {h/w:.2f}:1（推奨 1.6:1）")
    else:
        errors.append(f"表紙が見つかりません: {cover}")

    for w_ in warns:
        print("WARN ", w_)
    for e in errors:
        print("ERROR", e)
    if errors:
        sys.exit(1)
    print("OK: 入稿条件の自動チェックを通過しました（表示確認は Kindle Previewer で）")


if __name__ == "__main__":
    main()
