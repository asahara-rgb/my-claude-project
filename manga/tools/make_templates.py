#!/usr/bin/env python3
"""原稿用紙テンプレート（ガイド線付きPNG）を templates/ に生成する。

  python3 tools/make_templates.py            # book.json のサイズで生成
  python3 tools/make_templates.py --width 1600 --height 2560 --out templates

生成物:
  page_template.png        単ページ（左右どちらでも使える）
  page_template_left.png   左ページ用（ノド＝右辺）
  page_template_right.png  右ページ用（ノド＝左辺）
  spread_template.png      見開き1枚絵用（幅2倍）
"""
import argparse
import os

from PIL import Image, ImageDraw

from common import ROOT, load_book


def draw_guides(w, h, gutter_side=None, label=""):
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    safe = int(min(w, h) * 0.05)          # セーフエリア: 短辺の5%
    inner = int(min(w, h) * 0.11)         # 基本枠: 短辺の11%
    blue = (80, 150, 255)
    cyan = (120, 200, 230)
    red = (255, 120, 120)

    # 仕上がり枠
    d.rectangle([0, 0, w - 1, h - 1], outline=blue, width=4)
    # セーフエリア（点線風）
    step = 24
    for x in range(safe, w - safe, step * 2):
        d.line([x, safe, min(x + step, w - safe), safe], fill=cyan, width=3)
        d.line([x, h - safe, min(x + step, w - safe), h - safe], fill=cyan, width=3)
    for y in range(safe, h - safe, step * 2):
        d.line([safe, y, safe, min(y + step, h - safe)], fill=cyan, width=3)
        d.line([w - safe, y, w - safe, min(y + step, h - safe)], fill=cyan, width=3)
    # 基本枠
    d.rectangle([inner, inner, w - inner, h - inner], outline=blue, width=3)
    # 中心線（薄く）
    d.line([w // 2, 0, w // 2, h], fill=(225, 235, 250), width=2)
    d.line([0, h // 2, w, h // 2], fill=(225, 235, 250), width=2)
    # ノド側マーク
    if gutter_side == "right":
        d.rectangle([w - 18, 0, w - 1, h - 1], fill=red)
    elif gutter_side == "left":
        d.rectangle([0, 0, 18, h - 1], fill=red)
    # ラベル
    text = f"{label} {w}x{h}px  safe={safe}px  inner={inner}px"
    d.text((safe + 10, safe + 10), text, fill=blue)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--out", default=os.path.join(ROOT, "templates"))
    a = ap.parse_args()
    book = load_book()
    w = a.width or book["page_width"]
    h = a.height or book["page_height"]
    os.makedirs(a.out, exist_ok=True)

    outputs = {
        "page_template.png": draw_guides(w, h, None, "single"),
        "page_template_left.png": draw_guides(w, h, "right", "LEFT page (gutter=right)"),
        "page_template_right.png": draw_guides(w, h, "left", "RIGHT page (gutter=left)"),
    }
    spread = Image.new("RGB", (w * 2, h), "white")
    spread.paste(draw_guides(w, h, "right", "spread L"), (0, 0))
    spread.paste(draw_guides(w, h, "left", "spread R"), (w, 0))
    outputs["spread_template.png"] = spread

    for name, img in outputs.items():
        path = os.path.join(a.out, name)
        img.save(path, optimize=True)
        print("wrote", os.path.relpath(path, ROOT), img.size)


if __name__ == "__main__":
    main()
