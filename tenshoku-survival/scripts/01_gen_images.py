#!/usr/bin/env python3
"""コマ画像の生成。characters.json + style.json + コマ prompt を連結して画像生成を実行し raw/epNN/ に保存する。

  python3 scripts/01_gen_images.py --episode 1 --provider placeholder     # API不要。灰色のダミー画像
  python3 scripts/01_gen_images.py --episode 1 --provider prompts         # prompt をテキスト書き出しのみ（Midjourney/NovelAI/ComfyUI に手で投入）
  python3 scripts/01_gen_images.py --episode 1 --provider cmd \
      --cmd 'python3 my_sd.py --prompt "{prompt}" --negative "{negative}" --w {w} --h {h} --seed {seed} --out "{out}"'
  python3 scripts/01_gen_images.py --episode 1 --provider openai --dry-run   # OpenAI/Gemini はまず dry-run で確認
  python3 scripts/01_gen_images.py --episode 1 --provider gemini --variants 4
  python3 scripts/01_gen_images.py --episode 1 --only p02_c01            # 1コマだけ再生成

raw/refs/<キャラkey>_*.png（00_character_test.py の sheet モードで作った参照シート）があれば、
そのコマに映るキャラの参照画像を openai/gemini に同送する（一貫性のため）。

出力: raw/epNN/<panel_id>_<a|b|c|d>.png と同名 .txt（使ったプロンプト）
採用: pages.json の panel に "pick": "b" を書くと 03_build_pages.py がその案を使う（未指定は a）。
      --pick-first を付けると生成後に pick が空の panel へ "a" を書き戻す。

provider の追加: scripts/providers.py の PROVIDERS に関数を足す。
"""
import argparse
import glob
import os

from common import ROOT, build_prompt, load_specs, save_json
from providers import PROVIDERS

VARIANT_LETTERS = "abcdefgh"


def reference_images(specs, panel):
    """raw/refs/<char>_*.png があれば参照画像として渡す（00_character_test.py の sheet モードで作る）。"""
    refs = []
    for key in panel.get("characters", []):
        refs += sorted(glob.glob(os.path.join(ROOT, "raw", "refs", f"{key}_*.png")))[:2]
    return refs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--provider", default="placeholder", choices=["prompts"] + sorted(PROVIDERS))
    ap.add_argument("--cmd", help="provider=cmd のコマンドテンプレート。{prompt} {negative} {w} {h} {seed} {out} {refs}")
    ap.add_argument("--model", help="openai / gemini のモデル名を上書き")
    ap.add_argument("--no-refs", action="store_true", help="raw/refs/ の参照画像を使わない")
    ap.add_argument("--dry-run", action="store_true", help="API を呼ばずリクエスト内容を表示")
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
                ctx = {"refs": [] if a.no_refs else reference_images(specs, panel), "dry_run": a.dry_run, "cmd": a.cmd, "model": a.model}
                PROVIDERS[a.provider](prompt, negative, w, h, seed, out, ctx)
                if a.dry_run:
                    break          # 1 案分だけ表示
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
