#!/usr/bin/env python3
"""表紙を合成する。キービジュアル（AI生成画像）の上にタイトル・サブタイトル・著者名を Pillow で焼き込む。

  python3 scripts/05_build_cover.py --art raw/cover/key_visual_a.png --out build/cover.jpg
  python3 scripts/05_build_cover.py --out build/cover.jpg              # 画像なし（プレースホルダ地）

サイズは book.json の page_width/page_height（既定 1600x2560）。文字は右上から縦書き。
"""
import argparse
import importlib
import json
import os

from PIL import Image, ImageDraw, ImageFont

from common import ROOT, find_fonts

compose = importlib.import_module("02_compose_text")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art")
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "cover.jpg"))
    ap.add_argument("--book", default=os.path.join(ROOT, "book.json"))
    ap.add_argument("--volume", default="1")
    a = ap.parse_args()
    book = json.load(open(a.book, encoding="utf-8"))
    W, H = 1600, 2560
    reg, bold = find_fonts()

    if a.art and os.path.isfile(a.art):
        im = Image.open(a.art).convert("RGB")
        scale = max(W / im.width, H / im.height)
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        img = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
    else:
        img = Image.new("RGB", (W, H), (235, 235, 235))
        d0 = ImageDraw.Draw(img)
        for y in range(0, H, 48):
            d0.line([0, y, W, y], fill=(215, 215, 215), width=2)
    d = ImageDraw.Draw(img)

    title, sub = book["title"], book.get("subtitle", "")
    # 帯（下部）
    d.rectangle([0, H - 420, W, H], fill=(20, 20, 20))
    f_author = ImageFont.truetype(bold or reg, 64)
    f_sub = ImageFont.truetype(reg, 52)
    d.text((W - 80, H - 300), book.get("author", ""), font=f_author, fill="white", anchor="rm")
    d.text((80, H - 300), f"第{a.volume}巻", font=f_author, fill="white", anchor="lm")
    if sub:
        d.text((W // 2, H - 150), sub, font=f_sub, fill=(230, 230, 230), anchor="mm")

    # タイトル（縦書き・右上）
    cfg = {"font_size": 150, "font_size_small": 100, "max_chars_per_column": 8, "balloon_padding": 0,
           "balloon_border": 0, "line_gap": 1.05, "column_gap": 1.15}
    ts = compose.TextStyle(150, bold or reg, bold)
    cols = compose.balance_columns(compose.parse_emphasis(title), 8)
    tw, th, _, _ = compose.measure(cols, ts, 1.05, 1.15)
    compose.draw_vertical(d, cols, W - 120, 140, ts, 1.05, 1.15, fill="black", halo=("white", 16))

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    img.save(a.out, quality=92, optimize=True, subsampling=0)
    print("wrote", os.path.relpath(a.out, ROOT), img.size)


if __name__ == "__main__":
    main()
