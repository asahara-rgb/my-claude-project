#!/usr/bin/env python3
"""コマ画像の生成。characters.json + style.json + コマ prompt を連結して画像生成を実行し raw/epNN/ に保存する。

  python3 scripts/01_gen_images.py --episode 1 --provider placeholder     # API不要。灰色のダミー画像
  python3 scripts/01_gen_images.py --episode 1 --provider prompts         # prompt をテキスト書き出しのみ（Midjourney/NovelAI/ComfyUI に手で投入）
  python3 scripts/01_gen_images.py --episode 1 --provider cmd \
      --cmd 'python3 my_sd.py --prompt "{prompt}" --negative "{negative}" --w {w} --h {h} --seed {seed} --out "{out}"'
  python3 scripts/01_gen_images.py --episode 1 --only p02_c01            # 1コマだけ再生成

出力: raw/epNN/<panel_id>_<a|b|c|d>.png と同名 .txt（使ったプロンプト）
採用: pages.json の panel に "pick": "b" を書くと 03_build_pages.py がその案を使う（未指定は a）。
      --pick-first を付けると生成後に pick が空の panel へ "a" を書き戻す。

provider の追加: PROVIDERS に関数を足す（prompt, negative, w, h, seed, out_path）→ 画像を out_path に保存。
"""
import argparse
import os
import shlex
import subprocess

from PIL import Image, ImageDraw, ImageFont

from common import ROOT, build_prompt, find_fonts, load_specs, save_json

VARIANT_LETTERS = "abcdefgh"


def gen_placeholder(prompt, negative, w, h, seed, out):
    """API 不要のダミー。灰色地に panel id とプロンプト冒頭を描く。パイプライン検証用。"""
    img = Image.new("RGB", (w, h), (225, 225, 225))
    d = ImageDraw.Draw(img)
    for y in range(0, h, 40):
        d.line([0, y, w, y], fill=(205, 205, 205), width=1)
    d.rectangle([0, 0, w - 1, h - 1], outline=(120, 120, 120), width=6)
    d.line([0, 0, w, h], fill=(190, 190, 190), width=3)
    d.line([w, 0, 0, h], fill=(190, 190, 190), width=3)
    reg, _ = find_fonts()
    f_big = ImageFont.truetype(reg, int(w * 0.09))
    f_small = ImageFont.truetype(reg, int(w * 0.028))
    d.text((w // 2, h // 2 - w * 0.12), os.path.basename(out).rsplit(".", 1)[0], fill=(90, 90, 90), font=f_big, anchor="mm")
    words, lines, cur = prompt.split(", ")[-6:-1], [], ""
    for wd in words:
        if len(cur) + len(wd) > 42:
            lines.append(cur)
            cur = ""
        cur += wd + ", "
    lines.append(cur)
    for i, ln in enumerate(lines[:6]):
        d.text((w // 2, h // 2 + i * w * 0.04), ln.strip(", "), fill=(110, 110, 110), font=f_small, anchor="mm")
    img.save(out)


def gen_cmd(prompt, negative, w, h, seed, out, template):
    cmd = template.format(prompt=prompt.replace('"', "'"), negative=negative.replace('"', "'"), w=w, h=h, seed=seed, out=out)
    subprocess.run(cmd, shell=True, check=True)
    if not os.path.isfile(out):
        raise SystemExit(f"コマンドは成功しましたが出力がありません: {out}")


PROVIDERS = {"placeholder": gen_placeholder}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--provider", default="placeholder", choices=["placeholder", "prompts", "cmd"])
    ap.add_argument("--cmd", help="provider=cmd のコマンドテンプレート。{prompt} {negative} {w} {h} {seed} {out}")
    ap.add_argument("--variants", type=int, help="1コマの案数（既定 style.json の variants_per_panel）")
    ap.add_argument("--only", help="panel id（カンマ区切り）")
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--pick-first", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()

    specs = load_specs(a.episode)
    st = specs["style"]
    out_dir = os.path.join(ROOT, "raw", specs["ep"])
    os.makedirs(out_dir, exist_ok=True)
    n = a.variants or (1 if a.provider == "placeholder" else st.get("variants_per_panel", 4))
    only = set(a.only.split(",")) if a.only else None
    w, h = st["gen_width"], st["gen_height"]
    changed = False

    for page in specs["pages"]["pages"]:
        for panel in page["panels"]:
            if only and panel["id"] not in only:
                continue
            prompt = build_prompt(panel, specs)
            negative = st.get("negative_prompt", "")
            with open(os.path.join(out_dir, panel["id"] + ".txt"), "w", encoding="utf-8") as f:
                f.write(prompt + "\n\n[negative]\n" + negative + "\n")
            if a.provider == "prompts":
                print("prompt", panel["id"])
                continue
            for i in range(n):
                out = os.path.join(out_dir, f"{panel['id']}_{VARIANT_LETTERS[i]}.png")
                if os.path.exists(out) and not a.overwrite:
                    continue
                seed = a.seed + i
                if a.provider == "cmd":
                    if not a.cmd:
                        raise SystemExit("--cmd を指定してください")
                    gen_cmd(prompt, negative, w, h, seed, out, a.cmd)
                else:
                    PROVIDERS[a.provider](prompt, negative, w, h, seed, out)
                print("gen", os.path.relpath(out, ROOT))
            if a.pick_first and not panel.get("pick"):
                panel["pick"] = "a"
                changed = True
    if changed:
        save_json(specs["pages_path"], specs["pages"])
        print("pick を書き戻しました:", os.path.relpath(specs["pages_path"], ROOT))
    if a.provider == "prompts":
        print(f"\nプロンプトを {os.path.relpath(out_dir, ROOT)}/*.txt に書き出しました。生成した画像は <panel_id>_a.png の名前で同じフォルダに置いてください。")


if __name__ == "__main__":
    main()
