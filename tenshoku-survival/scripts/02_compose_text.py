#!/usr/bin/env python3
"""吹き出し＋縦書き日本語セリフの描画ライブラリ（03_build_pages.py から import して使う）。

単体実行で描画テストができる:
  python3 scripts/02_compose_text.py --text "書類選考は「読む」作業じゃない。\n**「外す」作業なんです。**" --type speech --out /tmp/test.png

対応:
  - 縦書き（右→左の段組）、禁則処理（行頭禁止文字のぶら下げ、行末禁止文字の追い出し）
  - 縦中横なし。ASCII の ? ! は全角化。「ー」「〜」「…」「（」「」」等は 90° 回転、小書き仮名・句読点は右上寄せ
  - **太字** 強調（Bold フォントがあれば切替、無ければストロークで擬似太字）
  - 吹き出し種別: speech(楕円) / thought(雲) / shout(トゲ) / narration(角箱) / mono(枠なし・白フチ文字) / title / next
  - 改行 \n は段（列）の強制改行
"""
import argparse
import math
import re

from PIL import Image, ImageDraw, ImageFont

from common import find_fonts

ROTATE = set("ー〜～…‥—–―（）「」『』［］｛｝〈〉《》【】〔〕()[]{}<>-=＝：；:;")
UPPER_RIGHT = set("、。，．,.")
SMALL_KANA = set("ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ")
NO_LINE_START = set("、。，．・：；？！ーぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ」』）］｝〉》】〕…‥")
NO_LINE_END = set("「『（［｛〈《【〔")
TO_FULL = {"?": "？", "!": "！", "(": "（", ")": "）", " ": "　", "~": "〜", "-": "ー"}


class TextStyle:
    _cache = {}

    def __init__(self, size, regular, bold=None):
        self.size = size
        self.regular_path, self.bold_path = regular, bold
        self.font = ImageFont.truetype(regular, size)
        self.bold = ImageFont.truetype(bold, size) if bold else None
        self.fake_bold = bold is None

    def scaled(self, factor):
        """同じフォントで size を factor 倍した TextStyle（キャッシュ）。"""
        size = max(10, int(round(self.size * factor)))
        key = (size, self.regular_path, self.bold_path)
        if key not in TextStyle._cache:
            TextStyle._cache[key] = TextStyle(size, self.regular_path, self.bold_path)
        return TextStyle._cache[key]


def normalize(text):
    return "".join(TO_FULL.get(c, c) for c in text)


def parse_emphasis(text):
    """'a **b** c' → [(char, bold_flag), ...]。改行は ('\\n', False)。"""
    out, bold = [], False
    for tok in re.split(r"(\*\*)", text):
        if tok == "**":
            bold = not bold
            continue
        for c in normalize(tok):
            out.append((c, bold))
    return out


def wrap_columns(chars, max_per_col):
    """縦書きの段（列）に分割。禁則: 行頭禁止文字はぶら下げ（前の列に追加）、行末禁止文字は次の列へ。"""
    cols, cur = [], []
    for c, b in chars:
        if c == "\n":
            cols.append(cur)
            cur = []
            continue
        if len(cur) >= max_per_col:
            if c in NO_LINE_START and len(cur) <= max_per_col + 1:
                cur.append((c, b))          # ぶら下げ
                continue
            if cur and cur[-1][0] in NO_LINE_END:
                carry = cur.pop()           # 追い出し
                cols.append(cur)
                cur = [carry, (c, b)]
                continue
            cols.append(cur)
            cur = []
        cur.append((c, b))
    if cur or not cols:
        cols.append(cur)
    return cols


def balance_columns(chars, max_per_col):
    """全体の文字数から列数を決め、各列の長さをなるべく均等にする（吹き出しが正方形に近くなる）。"""
    n = sum(1 for c, _ in chars if c != "\n")
    if "\n" in [c for c, _ in chars]:
        return wrap_columns(chars, max_per_col)
    ncol = max(1, math.ceil(n / max_per_col))
    per = math.ceil(n / ncol)
    return wrap_columns(chars, max(per, 2))


def measure(cols, ts, line_gap, col_gap):
    ch = ts.size * line_gap
    cw = ts.size * col_gap
    h = max((len(c) for c in cols), default=1) * ch
    w = len(cols) * cw
    return int(w), int(h), ch, cw


def draw_vertical(draw, cols, x_right, y_top, ts, line_gap, col_gap, fill="black", halo=None):
    """右上 (x_right, y_top) から左方向に段を並べて描く。halo=(color,width) で文字の白フチ。"""
    ch = ts.size * line_gap
    cw = ts.size * col_gap
    s = ts.size
    for ci, col in enumerate(cols):
        cx = x_right - cw * ci - cw / 2       # 列の中心 x
        for ri, (c, bold) in enumerate(col):
            cy = y_top + ch * ri + ch / 2      # 文字の中心 y
            font = ts.bold if (bold and ts.bold) else ts.font
            stroke = (1 if (bold and ts.fake_bold) else 0)
            if c in ROTATE:
                glyph = Image.new("L", (s * 2, s * 2), 0)
                gd = ImageDraw.Draw(glyph)
                gd.text((s, s), c, font=font, fill=255, anchor="mm", stroke_width=stroke)
                glyph = glyph.rotate(-90, resample=Image.BICUBIC)
                if halo:
                    hg = Image.new("L", glyph.size, 0)
                    ImageDraw.Draw(hg).text((s, s), c, font=font, fill=255, anchor="mm", stroke_width=halo[1] + stroke)
                    hg = hg.rotate(-90, resample=Image.BICUBIC)
                    draw._image.paste(halo[0], (int(cx - s), int(cy - s)), hg)
                draw._image.paste(fill, (int(cx - s), int(cy - s)), glyph)
                continue
            dx = dy = 0
            if c in UPPER_RIGHT:
                dx, dy = s * 0.28, -s * 0.28
            elif c in SMALL_KANA:
                dx, dy = s * 0.10, -s * 0.08
            pos = (cx + dx, cy + dy)
            if halo:
                draw.text(pos, c, font=font, fill=halo[0], anchor="mm", stroke_width=halo[1] + stroke, stroke_fill=halo[0])
            draw.text(pos, c, font=font, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=fill)


# ---------------------------------------------------------------- 吹き出し形状

def _ellipse_pts(cx, cy, rx, ry, n=72):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def shape_speech(d, box, border, tail=None):
    x0, y0, x1, y1 = box
    d.ellipse(box, fill="white", outline="black", width=border)
    if tail:
        _tail(d, box, tail, border)


def shape_thought(d, box, border):
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    n = max(10, int((rx + ry) / 22))
    r = (rx + ry) / n * 0.95
    for i in range(n):
        a = 2 * math.pi * i / n
        px, py = cx + (rx - r * 0.6) * math.cos(a), cy + (ry - r * 0.6) * math.sin(a)
        d.ellipse([px - r, py - r, px + r, py + r], fill="white", outline="black", width=border)
    d.ellipse([x0 + r * 0.7, y0 + r * 0.7, x1 - r * 0.7, y1 - r * 0.7], fill="white")


def shape_shout(d, box, border):
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    pts, n = [], 22
    for i in range(n * 2):
        a = 2 * math.pi * i / (n * 2)
        k = 1.0 if i % 2 == 0 else 0.78
        pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    d.polygon(pts, fill="white", outline="black", width=border)


def shape_box(d, box, border):
    d.rectangle(box, fill="white", outline="black", width=border)


def _tail(d, box, tail, border):
    """tail: 'down-left' 等。楕円の縁から外へ小さな三角。"""
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    ang = {"down": 90, "up": -90, "left": 180, "right": 0, "down-left": 135, "down-right": 45, "up-left": -135, "up-right": -45}[tail]
    a = math.radians(ang)
    bx, by = cx + rx * 0.92 * math.cos(a), cy + ry * 0.92 * math.sin(a)
    tx, ty = cx + (rx + 46) * math.cos(a), cy + (ry + 46) * math.sin(a)
    w = 0.22
    p1 = (cx + rx * 0.95 * math.cos(a - w), cy + ry * 0.95 * math.sin(a - w))
    p2 = (cx + rx * 0.95 * math.cos(a + w), cy + ry * 0.95 * math.sin(a + w))
    d.polygon([p1, (tx, ty), p2], fill="white", outline="black", width=border)
    d.polygon([p1, (bx, by), p2], fill="white")


# ---------------------------------------------------------------- 吹き出し1個の描画

def render_balloon(img, balloon, ts_regular, ts_small, cfg, cell, ts_title=None):
    """balloon(dict) を cell(x0,y0,x1,y1) 内の anchor 位置に描く。戻り値は占有 box。"""
    d = ImageDraw.Draw(img)
    btype = balloon.get("type", "speech")
    ts = ts_small if btype in ("narration", "mono", "next") else ts_regular
    if btype == "title" and ts_title:
        ts = ts_title
    pad = cfg["balloon_padding"]
    border = cfg["balloon_border"]
    lg, cg = cfg["line_gap"], cfg["column_gap"]
    max_col = cfg["max_chars_per_column"]
    if btype in ("narration", "next"):
        max_col = int(max_col * 1.4)

    chars = parse_emphasis(balloon["text"])
    x0, y0, x1, y1 = cell
    m = cfg.get("balloon_margin", 18)
    avail_w, avail_h = (x1 - x0) - m * 2, (y1 - y0) - m * 2
    if btype in ("speech",):
        fw, fh, pw, ph = 1.55, 1.25, 1.2, 1.4
    elif btype == "shout":
        fw, fh, pw, ph = 2.0, 1.4, 1.6, 1.8
    elif btype == "thought":
        fw, fh, pw, ph = 1.5, 1.28, 1.6, 1.8
    else:
        fw, fh, pw, ph = 1.0, 1.0, 1.8, 1.8

    # コマに収まるまで: 段の長さをコマの高さから決め、それでも幅が足りなければ文字を段階的に縮小
    base_ts = ts
    for factor in (1.0, 0.92, 0.85, 0.78, 0.72, 0.66, 0.6):
        ts = base_ts.scaled(factor)
        fit_col = int(((avail_h - pad * ph) / fh) / (ts.size * lg))
        mc = max(3, min(max_col, fit_col))
        cols = balance_columns(chars, mc)
        tw, th, _, _ = measure(cols, ts, lg, cg)
        bw, bh = tw * fw + pad * pw, th * fh + pad * ph
        if bw <= avail_w and bh <= avail_h:
            break
    anchor = balloon.get("anchor", "top-right")
    v, _, h = anchor.partition("-")
    if anchor == "center":
        v, h = "center", "center"
    if v == "top":
        by = y0 + m
    elif v == "bottom":
        by = y1 - m - bh
    else:
        by = (y0 + y1) / 2 - bh / 2
    if h == "right":
        bx = x1 - m - bw
    elif h == "left":
        bx = x0 + m
    else:
        bx = (x0 + x1) / 2 - bw / 2
    # セル内に収める
    bx = max(x0 + m, min(bx, x1 - m - bw))
    by = max(y0 + m, min(by, y1 - m - bh))
    box = [bx, by, bx + bw, by + bh]

    if btype == "speech":
        shape_speech(d, box, border, balloon.get("tail"))
    elif btype == "thought":
        shape_thought(d, box, border)
    elif btype == "shout":
        shape_shout(d, box, border)
    elif btype in ("narration", "next"):
        shape_box(d, box, border)
    # mono / title は枠なし

    tx_right = bx + bw / 2 + tw / 2
    ty_top = by + bh / 2 - th / 2
    halo = ("white", max(3, ts.size // 9)) if btype in ("mono", "title") else None
    draw_vertical(d, cols, tx_right, ty_top, ts, lg, cg, fill="black", halo=halo)
    return box


def make_text_styles(cfg):
    reg, bold = find_fonts()
    return (TextStyle(cfg["font_size"], reg, bold),
            TextStyle(cfg["font_size_small"], reg, bold),
            TextStyle(int(cfg["font_size"] * 1.6), bold or reg, bold))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--type", default="speech")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=34)
    a = ap.parse_args()
    cfg = {"font_size": a.size, "font_size_small": int(a.size * 0.85), "max_chars_per_column": 11,
           "balloon_padding": 26, "balloon_border": 4, "line_gap": 1.12, "column_gap": 1.35}
    img = Image.new("RGB", (600, 700), (200, 200, 200))
    ts, tss, tst = make_text_styles(cfg)
    render_balloon(img, {"type": a.type, "text": a.text.replace("\\n", "\n"), "anchor": "center", "tail": "down-left"}, ts, tss, cfg, (0, 0, 600, 700), tst)
    img.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
