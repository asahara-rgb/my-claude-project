#!/usr/bin/env python3
"""コマ画像をページレイアウトに合成し、吹き出し＋セリフを載せて 1ページ1画像に統合する。

  python3 scripts/03_build_pages.py --episode 1                  # build/pages/0001.jpg … を出力
  python3 scripts/03_build_pages.py --episode 1 --page 4 --preview   # 1ページだけ、composed/ に PNG

処理:
  1. spec/layouts.json のセルにコマ画像（raw/epNN/<id>_<pick>.png）を「はみ出し切り抜き（cover）」で配置
     panel.focus = "top"|"center"|"bottom" で切り抜き位置を選べる（既定 center）
  2. 枠線を引く（panel.border=false で枠なし、扉など）
  3. balloons を 02_compose_text.render_balloon で描画
  4. style.json の page_width x page_height にリサイズし、通しページ番号 0001.jpg で保存
     --start で通し番号の開始を指定（第2話以降を連結するとき）
"""
import argparse
import importlib
import os

from PIL import Image, ImageDraw

from common import ROOT, load_specs

compose = importlib.import_module("02_compose_text")


def cover_crop(im, w, h, focus="center"):
    scale = max(w / im.width, h / im.height)
    im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
    x = (im.width - w) // 2
    y = {"top": 0, "bottom": im.height - h}.get(focus, (im.height - h) // 2)
    return im.crop((x, y, x + w, y + h))


def panel_image(panel, raw_dir):
    pick = panel.get("pick", "a")
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = os.path.join(raw_dir, f"{panel['id']}_{pick}{ext}")
        if os.path.isfile(p):
            return Image.open(p).convert("RGB")
    raise SystemExit(f"コマ画像がありません: {panel['id']}_{pick}.png  → 01_gen_images.py を実行するか raw/ に置いてください")


def build_page(page, specs, styles, scale=2.0):
    """内部では page_width*scale で描いて最後に縮小（線と文字を滑らかにする）。"""
    st = specs["style"]
    W, H = int(st["page_width"] * scale), int(st["page_height"] * scale)
    margin = int(st["page_margin"] * scale)
    gx, gy = int(st["gutter_x"] * scale), int(st["gutter_y"] * scale)
    border = int(st["panel_border"] * scale)
    cfg = dict(st)
    for k in ("font_size", "font_size_small", "font_size_narration", "balloon_padding", "balloon_border"):
        cfg[k] = int(st[k] * scale)
    cfg["balloon_margin"] = int(18 * scale)

    layout = specs["layouts"][page["layout"]]
    cells = layout["cells"]
    if len(cells) != len(page["panels"]):
        raise SystemExit(f"p{page['page']}: layout '{page['layout']}' は {len(cells)} コマ、pages.json は {len(page['panels'])} コマ")

    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    iw, ih = W - margin * 2, H - margin * 2
    raw_dir = os.path.join(ROOT, "raw", specs["ep"])
    ts, tss, tst = styles

    for cell, panel in zip(cells, page["panels"]):
        x0 = margin + cell["x"] * iw + (gx / 2 if cell["x"] > 0 else 0)
        y0 = margin + cell["y"] * ih + (gy / 2 if cell["y"] > 0 else 0)
        x1 = margin + (cell["x"] + cell["w"]) * iw - (gx / 2 if cell["x"] + cell["w"] < 0.999 else 0)
        y1 = margin + (cell["y"] + cell["h"]) * ih - (gy / 2 if cell["y"] + cell["h"] < 0.999 else 0)
        x0, y0, x1, y1 = map(int, (x0, y0, x1, y1))
        art = cover_crop(panel_image(panel, raw_dir), x1 - x0, y1 - y0, panel.get("focus", "center"))
        img.paste(art, (x0, y0))
        if panel.get("border", True):
            d.rectangle([x0, y0, x1 - 1, y1 - 1], outline="black", width=border)
        for b in panel.get("balloons", []):
            compose.render_balloon(img, b, ts, tss, cfg, (x0, y0, x1, y1), tst)

    return img.resize((st["page_width"], st["page_height"]), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--page", type=int, help="このページだけ")
    ap.add_argument("--start", type=int, default=1, help="通しページ番号の開始")
    ap.add_argument("--preview", action="store_true", help="composed/epNN/ に PNG で出す（build/ には出さない）")
    ap.add_argument("--out", help="出力フォルダ（既定 build/pages）")
    a = ap.parse_args()

    specs = load_specs(a.episode)
    st = specs["style"]
    styles = compose.make_text_styles({k: int(v * 2.0) if k in ("font_size", "font_size_small") else v for k, v in st.items()})
    out_dir = a.out or (os.path.join(ROOT, "composed", specs["ep"]) if a.preview else os.path.join(ROOT, "build", "pages"))
    os.makedirs(out_dir, exist_ok=True)

    for page in specs["pages"]["pages"]:
        if a.page and page["page"] != a.page:
            continue
        img = build_page(page, specs, styles)
        n = a.start + page["page"] - 1
        if a.preview:
            dest = os.path.join(out_dir, f"p{page['page']:02d}.png")
            img.save(dest, optimize=True)
        else:
            dest = os.path.join(out_dir, f"{n:04d}.jpg")
            img.save(dest, quality=st.get("jpeg_quality", 88), optimize=True, subsampling=0)
        print(f"page {page['page']:2d} -> {os.path.relpath(dest, ROOT)}  {img.size[0]}x{img.size[1]}")


if __name__ == "__main__":
    main()
