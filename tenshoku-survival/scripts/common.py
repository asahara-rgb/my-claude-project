"""スクリプト共通: パス解決・spec 読み込み・フォント検索。"""
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "spec")
FONT_CANDIDATES = [
    # fonts/ に置いた商用可フォントを最優先（ファイル名に bold/Bold が付くものは太字用）
    os.path.join(ROOT, "fonts", "*.ttf"), os.path.join(ROOT, "fonts", "*.otf"),
    # システム
    "/usr/share/fonts/**/NotoSansCJK*-Regular*", "/usr/share/fonts/**/NotoSansJP-Regular*",
    "/usr/share/fonts/**/SourceHanSans*-Regular*", "/usr/share/fonts/**/ipag*.ttf",
    "/usr/share/fonts/**/fonts-japanese-gothic.ttf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", "C:/Windows/Fonts/meiryo.ttc", "C:/Windows/Fonts/YuGothM.ttc",
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_specs(episode):
    ep = f"ep{int(episode):02d}"
    return {
        "ep": ep,
        "characters": load_json(os.path.join(SPEC, "characters.json")),
        "style": load_json(os.path.join(SPEC, "style.json")),
        "layouts": load_json(os.path.join(SPEC, "layouts.json")),
        "pages": load_json(os.path.join(SPEC, ep, "pages.json")),
        "pages_path": os.path.join(SPEC, ep, "pages.json"),
    }


def find_fonts():
    """(regular, bold) のフォントパス。bold が無ければ None。"""
    regular = bold = None
    for pat in FONT_CANDIDATES:
        for p in sorted(glob.glob(pat, recursive=True)):
            if re.search(r"bold|black|heavy|W6|W7|W8", os.path.basename(p), re.I):
                bold = bold or p
            else:
                regular = regular or p
        if regular:
            break
    if not regular:
        raise SystemExit("日本語フォントが見つかりません。fonts/ に .ttf/.otf を置いてください（fonts/README.md 参照）")
    return regular, bold


def build_prompt(panel, specs):
    """style + キャラ固定プロンプト + コマプロンプト を連結。"""
    st, chars = specs["style"], specs["characters"]
    parts = [st["style_prefix"]]
    for key in panel.get("characters", []):
        if key in chars:
            parts.append(chars[key]["prompt"])
    parts.append(panel["prompt"])
    parts.append(st["style_suffix"])
    return ", ".join(p.strip().rstrip(",") for p in parts if p)
