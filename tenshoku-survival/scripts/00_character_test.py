#!/usr/bin/env python3
"""キャラ一貫性の検証（仕様書 §5-2「試し生成を20枚回して一貫性を検証」）。

  # 1) 参照シート（正面・横・斜め・表情）を各キャラ 2 枚生成 → raw/refs/<key>_1.png, _2.png
  python3 scripts/00_character_test.py sheet --provider gemini
  # 2) 20 パターン（構図・表情・画角）を生成 → raw/test/<key>_01.png …（refs があれば同送）
  python3 scripts/00_character_test.py test --provider gemini --count 20
  # 3) 見比べ用の一覧画像 → raw/test/contact_<key>.png
  python3 scripts/00_character_test.py sheet-view

判定の目安（docs/image_tool_recommendation.md）:
  20 枚中 16 枚以上（80%）で「髪型・眼鏡・服装・顔の印象」が同一人物に見える → 実用可
  それ以下 → 参照画像を差し替えて再試行、それでもダメなら LoRA 学習 or 外注へ
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

from common import ROOT, find_fonts, load_json, SPEC
from providers import PROVIDERS

SHEET_PROMPTS = [
    "character reference sheet, same character shown three times side by side: front view, three-quarter view, profile view, full body, neutral expression, standing, plain white background",
    "character expression sheet, same character's face shown six times in a grid: neutral, slight smile, surprised, worried, determined, tired, bust shots, plain white background",
]

TEST_SHOTS = [
    "bust shot, looking at viewer, neutral expression", "close-up of face, tired eyes, faint bitter smile",
    "full body standing in a crowded station concourse at dusk, wide shot", "sitting alone on a late-night train, harsh fluorescent light",
    "over-the-shoulder view reading a smartphone, shoulders slumped", "sitting in an office meeting room, hands on knees, nervous",
    "leaning forward across a table, agitated", "looking down at documents in hands", "frozen in shock, sweat drop, dramatic shading",
    "covering mouth with one hand", "looking up with new determination", "taking notes quickly in a small notebook",
    "walking out of an office building into evening city light, straighter posture", "at a desk at home at night, laptop open, writing intensely",
    "profile view, looking out a window", "low angle shot from below, standing", "high angle shot from above, sitting at desk",
    "three-quarter view, arms crossed, calm", "holding up one finger, explaining", "standing at a door looking back over shoulder",
]


def run(provider, ctx, prompts, out_paths, w, h, seed):
    for i, (p, out) in enumerate(zip(prompts, out_paths)):
        if os.path.exists(out) and not ctx.get("overwrite"):
            print("skip", os.path.relpath(out, ROOT))
            continue
        PROVIDERS[provider](p, ctx["negative"], w, h, seed + i, out, ctx)
        if not ctx.get("dry_run"):
            print("gen", os.path.relpath(out, ROOT))


def contact_sheet(paths, out, cols=5, cell=(300, 450)):
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        return
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell[0], rows * (cell[1] + 28)), "white")
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(find_fonts()[0], 18)
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB")
        im.thumbnail(cell)
        x, y = (i % cols) * cell[0], (i // cols) * (cell[1] + 28)
        sheet.paste(im, (x + (cell[0] - im.width) // 2, y))
        d.text((x + 6, y + cell[1] + 4), os.path.basename(p), fill="black", font=font)
    sheet.save(out)
    print("wrote", os.path.relpath(out, ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sheet", "test", "sheet-view"])
    ap.add_argument("--provider", default="placeholder", choices=sorted(PROVIDERS))
    ap.add_argument("--chars", default="yota,rei")
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--cmd")
    ap.add_argument("--model")
    ap.add_argument("--seed", type=int, default=5000)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    chars = load_json(os.path.join(SPEC, "characters.json"))
    st = load_json(os.path.join(SPEC, "style.json"))
    keys = [k for k in a.chars.split(",") if k in chars]
    ref_dir, test_dir = os.path.join(ROOT, "raw", "refs"), os.path.join(ROOT, "raw", "test")
    os.makedirs(ref_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)

    for key in keys:
        c = chars[key]
        base = lambda extra: f"{st['style_prefix']}, {c['prompt']}, {extra}, {st['style_suffix']}"
        ctx = {"negative": st.get("negative_prompt", ""), "dry_run": a.dry_run, "cmd": a.cmd, "model": a.model, "overwrite": a.overwrite}
        if a.mode == "sheet":
            prompts = [base(p) for p in SHEET_PROMPTS]
            outs = [os.path.join(ref_dir, f"{key}_{i+1}.png") for i in range(len(prompts))]
            ctx["refs"] = []
            run(a.provider, ctx, prompts, outs, st["gen_width"], st["gen_width"], a.seed)   # シートは正方形
            with open(os.path.join(ref_dir, f"{key}_prompts.txt"), "w", encoding="utf-8") as f:
                f.write("\n\n".join(prompts))
        elif a.mode == "test":
            shots = TEST_SHOTS[: a.count]
            prompts = [base(p) for p in shots]
            outs = [os.path.join(test_dir, f"{key}_{i+1:02d}.png") for i in range(len(prompts))]
            ctx["refs"] = [p for p in (os.path.join(ref_dir, f"{key}_{i}.png") for i in (1, 2)) if os.path.isfile(p)]
            if not ctx["refs"]:
                print(f"注意: raw/refs/{key}_*.png が無いので参照画像なしで生成します（先に sheet モードを推奨）")
            run(a.provider, ctx, prompts, outs, st["gen_width"], st["gen_height"], a.seed)
            with open(os.path.join(test_dir, f"{key}_prompts.txt"), "w", encoding="utf-8") as f:
                f.write("\n\n".join(f"{i+1:02d}: {p}" for i, p in enumerate(prompts)))
        else:
            contact_sheet([os.path.join(test_dir, f"{key}_{i+1:02d}.png") for i in range(a.count)], os.path.join(test_dir, f"contact_{key}.png"))
            contact_sheet([os.path.join(ref_dir, f"{key}_{i}.png") for i in (1, 2)], os.path.join(ref_dir, f"contact_{key}.png"), cols=2, cell=(500, 500))


if __name__ == "__main__":
    main()
