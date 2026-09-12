"""画像生成プロバイダ。01_gen_images.py / 00_character_test.py から使う。

各関数のシグネチャ: gen(prompt, negative, w, h, seed, out_path, ctx) -> None（out_path に PNG/JPEG を保存）
ctx: {"refs": [参照画像パス...], "dry_run": bool, "cmd": str|None, "model": str|None}

対応:
  placeholder  API 不要のダミー（パイプライン検証用）
  cmd          任意の CLI（ComfyUI / sd-webui / 自作スクリプト等）をテンプレートで呼ぶ
  openai       OpenAI Images API（gpt-image 系）。参照画像があれば /v1/images/edits、無ければ /v1/images/generations
               env OPENAI_API_KEY
  gemini       Gemini API generateContent（画像出力対応モデル）。参照画像は inlineData で同送
               env GEMINI_API_KEY（または GOOGLE_API_KEY）

※ openai / gemini はこの環境から API に到達できなかったため **実通信は未検証**。まず --dry-run で
  リクエスト内容を確認し、エラーが出たら各社の最新ドキュメントに合わせて `_openai` / `_gemini` を直す。
  モデル名は env で上書きできる: OPENAI_IMAGE_MODEL / GEMINI_IMAGE_MODEL
"""
import base64
import json
import mimetypes
import os
import subprocess
import urllib.request
import uuid

from PIL import Image, ImageDraw, ImageFont

from common import find_fonts

OPENAI_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")


def _http_json(url, body, headers, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _http_multipart(url, fields, files, headers, timeout=180):
    boundary = "----tenshoku" + uuid.uuid4().hex
    body = bytearray()
    for k, v in fields:
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    for k, path in files:
        mt = mimetypes.guess_type(path)[0] or "application/octet-stream"
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{os.path.basename(path)}\"\r\nContent-Type: {mt}\r\n\r\n".encode()
        body += open(path, "rb").read() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=bytes(body), headers={"Content-Type": f"multipart/form-data; boundary={boundary}", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _save_b64(b64, out):
    with open(out, "wb") as f:
        f.write(base64.b64decode(b64))


# ------------------------------------------------------------------ placeholder

def gen_placeholder(prompt, negative, w, h, seed, out, ctx):
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


# ------------------------------------------------------------------ cmd

def gen_cmd(prompt, negative, w, h, seed, out, ctx):
    template = ctx.get("cmd")
    if not template:
        raise SystemExit("--cmd を指定してください（{prompt} {negative} {w} {h} {seed} {out} {refs} が使えます）")
    refs = " ".join(f'"{r}"' for r in ctx.get("refs", []))
    cmd = template.format(prompt=prompt.replace('"', "'"), negative=negative.replace('"', "'"), w=w, h=h, seed=seed, out=out, refs=refs)
    if ctx.get("dry_run"):
        print("[dry-run]", cmd)
        return
    subprocess.run(cmd, shell=True, check=True)
    if not os.path.isfile(out):
        raise SystemExit(f"コマンドは成功しましたが出力がありません: {out}")


# ------------------------------------------------------------------ openai

def _openai_size(w, h):
    # gpt-image 系の対応サイズ（1024x1024 / 1024x1536 縦 / 1536x1024 横）に丸める。細かい比率は 03 の cover 切り抜きで吸収
    if h > w * 1.15:
        return "1024x1536"
    if w > h * 1.15:
        return "1536x1024"
    return "1024x1024"


def gen_openai(prompt, negative, w, h, seed, out, ctx):
    key = os.environ.get("OPENAI_API_KEY")
    if not key and not ctx.get("dry_run"):
        raise SystemExit("OPENAI_API_KEY が未設定です")
    headers = {"Authorization": f"Bearer {key or 'sk-...'}"}
    full_prompt = prompt + (f". Avoid: {negative}" if negative else "")
    refs = ctx.get("refs", [])
    model = ctx.get("model") or OPENAI_IMAGE_MODEL
    if refs:
        url = "https://api.openai.com/v1/images/edits"
        fields = [("model", model), ("prompt", "Use the attached images as the character reference sheet. " + full_prompt),
                  ("size", _openai_size(w, h)), ("quality", "high"), ("n", "1")]
        files = [("image[]", r) for r in refs]
        if ctx.get("dry_run"):
            print("[dry-run] POST", url, json.dumps(dict(fields), ensure_ascii=False, indent=1), "files:", [os.path.basename(r) for r in refs])
            return
        res = _http_multipart(url, fields, files, headers)
    else:
        url = "https://api.openai.com/v1/images/generations"
        body = {"model": model, "prompt": full_prompt, "size": _openai_size(w, h), "quality": "high", "n": 1, "output_format": "png"}
        if ctx.get("dry_run"):
            print("[dry-run] POST", url, json.dumps(body, ensure_ascii=False, indent=1))
            return
        res = _http_json(url, body, headers)
    _save_b64(res["data"][0]["b64_json"], out)


# ------------------------------------------------------------------ gemini

def _gemini_aspect(w, h):
    r = w / h
    for name, val in (("9:16", 9 / 16), ("2:3", 2 / 3), ("3:4", 3 / 4), ("1:1", 1.0), ("4:3", 4 / 3), ("3:2", 3 / 2), ("16:9", 16 / 9)):
        if abs(r - val) < 0.06:
            return name
    return "2:3" if r < 1 else "3:2"


def gen_gemini(prompt, negative, w, h, seed, out, ctx):
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key and not ctx.get("dry_run"):
        raise SystemExit("GEMINI_API_KEY が未設定です")
    model = ctx.get("model") or GEMINI_IMAGE_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    parts = []
    for r in ctx.get("refs", []):
        mt = mimetypes.guess_type(r)[0] or "image/png"
        parts.append({"inlineData": {"mimeType": mt, "data": base64.b64encode(open(r, "rb").read()).decode() if not ctx.get("dry_run") else "<base64>"}})
    text = ("Use the attached images as the exact character reference sheet; keep face, hair and outfit identical. " if parts else "") + prompt
    if negative:
        text += f". Do not include: {negative}"
    parts.append({"text": text})
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": _gemini_aspect(w, h)}}}
    if ctx.get("dry_run"):
        print("[dry-run] POST", url, json.dumps(body, ensure_ascii=False, indent=1)[:1500])
        return
    res = _http_json(url, body, {"x-goog-api-key": key})
    for part in res["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            _save_b64(part["inlineData"]["data"], out)
            return
    raise SystemExit(f"画像が返りませんでした: {json.dumps(res, ensure_ascii=False)[:500]}")


PROVIDERS = {"placeholder": gen_placeholder, "cmd": gen_cmd, "openai": gen_openai, "gemini": gen_gemini}
