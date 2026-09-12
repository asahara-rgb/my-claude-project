"""build/check/prepare で共有する小さなユーティリティ。"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_EXT = (".png", ".jpg", ".jpeg")
PAGE_RE = re.compile(r"^p?(\d{1,4})(?:[-_](\d{1,4}))?\b", re.IGNORECASE)


def load_book(path=None):
    path = path or os.path.join(ROOT, "book.json")
    with open(path, encoding="utf-8") as f:
        book = json.load(f)
    book.setdefault("direction", "rtl")
    book.setdefault("first_page_side", "left")
    book.setdefault("page_width", 1600)
    book.setdefault("page_height", 2560)
    book.setdefault("pages_dir", "pages")
    book.setdefault("cover", "cover/cover.jpg")
    book.setdefault("output", "dist/manga.epub")
    book.setdefault("language", "ja")
    book.setdefault("chapters", [])
    book["_path"] = path
    return book


def resolve(book, p):
    """book.json からの相対パスを絶対パスに。"""
    if os.path.isabs(p):
        return p
    return os.path.normpath(os.path.join(os.path.dirname(book["_path"]), p))


def sort_key(name):
    m = PAGE_RE.match(os.path.splitext(name)[0])
    if m:
        return (0, int(m.group(1)), name)
    return (1, 0, name)


def list_pages(pages_dir):
    if not os.path.isdir(pages_dir):
        sys.exit(f"ページフォルダが見つかりません: {pages_dir}")
    names = [n for n in os.listdir(pages_dir) if n.lower().endswith(IMAGE_EXT) and not n.startswith(".")]
    names.sort(key=sort_key)
    return [os.path.join(pages_dir, n) for n in names]


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"
