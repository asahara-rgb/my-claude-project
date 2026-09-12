#!/usr/bin/env python3
"""原稿画像を入稿サイズに揃えて dist/pages に書き出す。

  python3 tools/prepare_pages.py                       # pages/ → dist/pages/
  python3 tools/prepare_pages.py --in pages --out dist/pages --format auto --quality 90

- 縦長画像は高さを page_height に合わせて縮小（拡大はしない）。縦横比が違う場合は
  白（--fill で変更可）で余白を付けて page_width x page_height にする。
- 横長画像は見開きとして (page_width*2) x page_height に同様に揃える。
- --format auto: グレースケール（彩度がほぼ無い）画像は PNG(L)、カラーは JPEG。
- 透過は白で潰す。EXIF 回転を反映。
"""
import argparse
import os

from PIL import Image, ImageChops, ImageOps

from common import ROOT, list_pages, load_book, resolve


def is_grayscale(im, sample=200, tolerance=12):
    small = im.convert("RGB").resize((sample, max(1, int(sample * im.height / im.width))))
    r, g, b = small.split()
    return (ImageChops.difference(r, g).getextrema()[1] <= tolerance
            and ImageChops.difference(g, b).getextrema()[1] <= tolerance)


def fit(im, tw, th, fill):
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", im.size, fill)
        bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[3])
        im = bg
    scale = min(tw / im.width, th / im.height, 1.0)
    if scale < 1.0:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", (tw, th), fill)
    canvas.paste(im, ((tw - im.width) // 2, (th - im.height) // 2))
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book")
    ap.add_argument("--in", dest="src")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "pages"))
    ap.add_argument("--format", choices=["auto", "png", "jpg"], default="auto")
    ap.add_argument("--quality", type=int, default=90)
    ap.add_argument("--fill", default="white")
    a = ap.parse_args()
    book = load_book(a.book)
    src = a.src or resolve(book, book["pages_dir"])
    W, H = book["page_width"], book["page_height"]
    os.makedirs(a.out, exist_ok=True)

    for p in list_pages(src):
        stem = os.path.splitext(os.path.basename(p))[0]
        with Image.open(p) as im:
            spread = im.width > im.height
            out = fit(im, W * 2 if spread else W, H, a.fill)
            gray = is_grayscale(out)
        fmt = a.format
        if fmt == "auto":
            fmt = "png" if gray else "jpg"
        if fmt == "png":
            if gray:
                out = out.convert("L")
            dest = os.path.join(a.out, stem + ".png")
            out.save(dest, optimize=True)
        else:
            dest = os.path.join(a.out, stem + ".jpg")
            out.save(dest, quality=a.quality, optimize=True, progressive=False, subsampling=0)
        print(f"{os.path.basename(p):28} -> {os.path.relpath(dest, ROOT)}  {out.width}x{out.height} {'spread' if spread else ''}")
    print("\n次: python3 tools/build_epub.py --pages", os.path.relpath(a.out, ROOT))


if __name__ == "__main__":
    main()
