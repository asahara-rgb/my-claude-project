#!/usr/bin/env python3
"""ページ画像から Kindle 向け固定レイアウト EPUB3（右開き・見開き対応）を生成する。

  python3 tools/build_epub.py                                   # book.json の設定で生成
  python3 tools/build_epub.py --pages dist/pages --out dist/x.epub
  python3 tools/build_epub.py --pages sample/pages --cover sample/cover.png --out dist/sample.epub

生成する EPUB の要点:
  - rendition:layout=pre-paginated / orientation=portrait / spread=landscape
  - spine page-progression-direction = book.json の direction (rtl)
  - 表紙と横長画像は page-spread-center、それ以外は left/right を交互に
  - Kindle 互換メタ (fixed-layout, original-resolution, book-type=comic, primary-writing-mode)
  - nav.xhtml（目次: 表紙 / chapters）
"""
import argparse
import datetime as dt
import mimetypes
import os
import uuid
import zipfile
from xml.sax.saxutils import escape

from PIL import Image

from common import ROOT, list_pages, load_book, resolve

XHTML_PAGE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}">
<head>
  <meta charset="utf-8"/>
  <title>{title}</title>
  <meta name="viewport" content="width={w}, height={h}"/>
  <link rel="stylesheet" type="text/css" href="../style/fixed.css"/>
</head>
<body>
  <div class="page" style="width:{w}px;height:{h}px;">
    <img src="../image/{img}" alt="{alt}" width="{w}" height="{h}"/>
  </div>
</body>
</html>
"""

CSS = """@charset "UTF-8";
html, body { margin: 0; padding: 0; }
body { background: #fff; }
.page { position: relative; overflow: hidden; margin: 0; padding: 0; }
.page img { position: absolute; top: 0; left: 0; margin: 0; padding: 0; display: block; }
"""

CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def media_type(path):
    mt = mimetypes.guess_type(path)[0]
    return mt or "application/octet-stream"


def build(book, pages, cover, out):
    W, H = book["page_width"], book["page_height"]
    rtl = book["direction"] == "rtl"
    lang = book["language"]
    title = book["title"]
    ident = book.get("identifier") or ""
    if not ident or "REPLACE" in ident:
        ident = "urn:uuid:" + str(uuid.uuid4())
        print(f"identifier が未設定のため生成しました: {ident}\n  → book.json に書いておくと再ビルド時も同じIDになります")
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    manifest, spine, files, nav_items = [], [], {}, []

    # --- cover
    cover_ext = os.path.splitext(cover)[1].lower()
    cover_img = "cover" + cover_ext
    with Image.open(cover) as im:
        cw, ch = im.size
    files[f"OEBPS/image/{cover_img}"] = open(cover, "rb").read()
    manifest.append(f'<item id="cover-image" href="image/{cover_img}" media-type="{media_type(cover)}" properties="cover-image"/>')
    files["OEBPS/text/cover.xhtml"] = XHTML_PAGE.format(lang=lang, title=escape(title), w=cw, h=ch, img=cover_img, alt=escape(title)).encode()
    manifest.append('<item id="cover" href="text/cover.xhtml" media-type="application/xhtml+xml"/>')
    spine.append('<itemref idref="cover" properties="rendition:page-spread-center"/>')
    nav_items.append(("text/cover.xhtml", "表紙"))

    # --- pages
    side = book["first_page_side"]  # 次の単ページが来る側
    chapters = {int(c["page"]): c["title"] for c in book["chapters"]}
    for idx, p in enumerate(pages, start=1):
        ext = os.path.splitext(p)[1].lower().replace(".jpeg", ".jpg")
        img = f"p{idx:03d}{ext}"
        with Image.open(p) as im:
            w, h = im.size
        if w > h:  # 見開き1枚絵: 2ページ分を占めるので左右の交互は据え置き
            props = "rendition:page-spread-center"
        else:
            props = f"rendition:page-spread-{side}"
            side = "right" if side == "left" else "left"
        files[f"OEBPS/image/{img}"] = open(p, "rb").read()
        manifest.append(f'<item id="img{idx:03d}" href="image/{img}" media-type="{media_type(p)}"/>')
        files[f"OEBPS/text/p{idx:03d}.xhtml"] = XHTML_PAGE.format(lang=lang, title=escape(f"{title} p{idx}"), w=w, h=h, img=img, alt=f"page {idx}").encode()
        manifest.append(f'<item id="p{idx:03d}" href="text/p{idx:03d}.xhtml" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="p{idx:03d}" properties="{props}"/>')
        if idx in chapters:
            nav_items.append((f"text/p{idx:03d}.xhtml", chapters[idx]))
        elif idx == 1:
            nav_items.append((f"text/p{idx:03d}.xhtml", "本文"))

    # --- nav
    li = "\n".join(f'      <li><a href="{href}">{escape(t)}</a></li>' for href, t in nav_items)
    nav = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}">
<head><meta charset="utf-8"/><title>目次</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>目次</h1>
    <ol>
{li}
    </ol>
  </nav>
</body>
</html>
"""
    files["OEBPS/nav.xhtml"] = nav.encode()
    manifest.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
    files["OEBPS/style/fixed.css"] = CSS.encode()
    manifest.append('<item id="css" href="style/fixed.css" media-type="text/css"/>')

    # --- opf
    def opt(tag, key, extra=""):
        v = book.get(key)
        if not v or v.startswith("["):  # 未記入・仮の値は出力しない
            return ""
        return f"    <{tag}{extra}>{escape(v)}</{tag}>\n"

    opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="{lang}" prefix="rendition: http://www.idpf.org/vocab/rendition/#">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{escape(ident)}</dc:identifier>
    <dc:title id="title">{escape(title)}</dc:title>
{'    <meta refines="#title" property="alternate-script" xml:lang="ja-Kana">' + escape(book["title_kana"]) + '</meta>' + chr(10) if book.get("title_kana") and not book["title_kana"].startswith("[") else ''}    <dc:creator id="creator">{escape(book.get("author", ""))}</dc:creator>
    <meta refines="#creator" property="role" scheme="marc:relators">aut</meta>
{'    <meta refines="#creator" property="alternate-script" xml:lang="ja-Kana">' + escape(book["author_kana"]) + '</meta>' + chr(10) if book.get("author_kana") and not book["author_kana"].startswith("[") else ''}{opt("dc:publisher", "publisher")}{opt("dc:description", "description")}    <dc:language>{lang}</dc:language>
    <meta property="dcterms:modified">{now}</meta>
    <meta property="rendition:layout">pre-paginated</meta>
    <meta property="rendition:orientation">portrait</meta>
    <meta property="rendition:spread">landscape</meta>
    <meta name="cover" content="cover-image"/>
    <meta name="fixed-layout" content="true"/>
    <meta name="original-resolution" content="{W}x{H}"/>
    <meta name="book-type" content="comic"/>
    <meta name="primary-writing-mode" content="{'horizontal-rl' if rtl else 'horizontal-lr'}"/>
    <meta name="region-mag" content="false"/>
    <meta name="zero-gutter" content="true"/>
    <meta name="zero-margin" content="true"/>
  </metadata>
  <manifest>
    {chr(10).join('    ' + m for m in manifest).strip()}
  </manifest>
  <spine page-progression-direction="{'rtl' if rtl else 'ltr'}">
    {chr(10).join('    ' + s for s in spine).strip()}
  </spine>
</package>
"""
    files["OEBPS/content.opf"] = opf.encode()
    files["META-INF/container.xml"] = CONTAINER.encode()

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, data in files.items():
            comp = zipfile.ZIP_STORED if name.startswith("OEBPS/image/") else zipfile.ZIP_DEFLATED
            z.writestr(name, data, compress_type=comp)
    size = os.path.getsize(out)
    print(f"wrote {out}  ({size/1024/1024:.1f} MB, {len(pages)} pages + cover, {'右開き' if rtl else '左開き'})")
    print("次: Kindle Previewer で開いて 見開き / スマホ縦 / Kindle端末 の3表示を確認")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book")
    ap.add_argument("--pages")
    ap.add_argument("--cover")
    ap.add_argument("--out")
    ap.add_argument("--title")
    ap.add_argument("--author")
    a = ap.parse_args()
    book = load_book(a.book)
    if a.title:
        book["title"] = a.title
    if a.author:
        book["author"] = a.author
    pages_dir = a.pages or resolve(book, book["pages_dir"])
    cover = a.cover or resolve(book, book["cover"])
    out = a.out or resolve(book, book["output"])
    if book["title"].startswith("["):
        print("WARN: book.json の title が仮の値のままです")
    pages = list_pages(pages_dir)
    if not pages:
        raise SystemExit(f"ページ画像がありません: {pages_dir}")
    if not os.path.isfile(cover):
        raise SystemExit(f"表紙が見つかりません: {cover}")
    build(book, pages, cover, out)


if __name__ == "__main__":
    main()
