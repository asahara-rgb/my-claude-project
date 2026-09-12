# 転職サバイバル 〜面接官だけが知る選考の秘密〜 制作パイプライン

仕様書 v1 §4「Claude Code 実装仕様」の実装。AI 生成したコマ画像に、プログラムで吹き出し・縦書きセリフを
合成し、ページに組んで右開き固定レイアウト EPUB（KDP 入稿用）まで作る。

```
tenshoku-survival/
├── book.json                 # EPUB メタデータ（タイトル・著者・章）
├── spec/
│   ├── characters.json       # キャラ固定プロンプト（yota / rei / _extra=顔なし脇役）
│   ├── style.json            # 共通スタイル指定・生成サイズ・ページサイズ・文字サイズ
│   ├── layouts.json          # ページレイアウト（セル配置。読み順＝右→左）
│   └── ep01/pages.json       # 第1話 全10ページ 36コマ：prompt / characters / balloons
├── raw/ep01/                 # 生成直後のコマ画像 <panel_id>_<a-d>.png と使用プロンプト .txt（git管理外）
├── composed/ep01/            # --preview 出力（PNG、確認用）
├── build/pages/0001.jpg …    # KDP 入稿用ページ画像
├── build/cover.jpg           # 表紙
├── build/*.epub              # 固定レイアウト EPUB
├── fonts/                    # セリフ用日本語フォント（商用可・埋め込み可のものを置く）
├── docs/ep01_name_review.md  # 第1話ネームのレビュー
└── scripts/
    ├── 01_gen_images.py      # プロンプト連結 → 画像生成（provider: placeholder / prompts / cmd）
    ├── 02_compose_text.py    # 吹き出し＋縦書きセリフ描画ライブラリ（禁則・太字・回転文字）
    ├── 03_build_pages.py     # コマをレイアウトに合成 → セリフ合成 → 1ページ1画像
    ├── 04_build_epub.py      # ../manga/tools/build_epub.py を呼んで右開き EPUB を生成
    └── 05_build_cover.py     # キービジュアルにタイトル等を焼き込んで表紙を作る
```

## 使い方

```bash
cd tenshoku-survival
pip install pillow

# 1. コマ画像
python3 scripts/01_gen_images.py --episode 1 --provider prompts        # プロンプトだけ書き出す（Midjourney / NovelAI / ComfyUI 等に投入）
#    → raw/ep01/<panel_id>.txt を読んで生成し、<panel_id>_a.png（案b,c,d は _b …）として raw/ep01/ に保存
#    ローカルSD等にCLIがあるなら:
python3 scripts/01_gen_images.py --episode 1 --provider cmd --cmd 'sd --prompt "{prompt}" --negative "{negative}" -W {w} -H {h} --seed {seed} -o "{out}"'
#    APIなしで流れだけ確認したい:
python3 scripts/01_gen_images.py --episode 1 --provider placeholder --pick-first

# 2. 採用案を選ぶ → spec/ep01/pages.json の各 panel に "pick": "b" を書く（未指定は a）

# 3. ページ合成（プレビュー → 本番）
python3 scripts/03_build_pages.py --episode 1 --preview     # composed/ep01/p01.png …
python3 scripts/03_build_pages.py --episode 1               # build/pages/0001.jpg …

# 4. 表紙と EPUB
python3 scripts/05_build_cover.py --art raw/cover/key_a.png
python3 scripts/04_build_epub.py
#    → build/tenshoku-survival.epub を Kindle Previewer で確認
```

第2話以降は `spec/ep02/pages.json` を追加し、`03_build_pages.py --episode 2 --start 11` のように通し番号を続け、
`book.json` の `chapters` に各話の開始ページを足す。

## pages.json の書き方

```jsonc
{
  "id": "p04_c03",                 // raw/ の画像名になる
  "name": "コマ3（中段・大）",       // メモ（ネームのコマ番号）
  "prompt": "dramatic composition, ...",   // コマ固有の指示。style/characters は自動で連結
  "characters": ["yota"],          // characters.json のキー。映る人物だけ
  "pick": "b",                     // 採用案（省略時 a）
  "focus": "top",                  // 切り抜き位置 top / center / bottom
  "border": false,                 // 枠線なし（扉など）
  "balloons": [
    { "type": "speech", "speaker": "rei", "text": "企業の人事はもっと短い。", "anchor": "top-right", "tail": "down-left" },
    { "type": "narration", "text": "翌週。", "anchor": "top-right" }
  ]
}
```

- `type`: `speech`（楕円）/ `thought`（雲）/ `shout`（トゲ）/ `narration`（角箱）/ `mono`（枠なし白フチ）/ `title` / `next`
- `anchor`: `top-right` `top-left` `bottom-right` `bottom-left` `center` など。セル内で自動的にはみ出し補正
- `text`: `\n` で段の強制改行、`**太字**` で強調。ASCII の `?` `!` は全角化される
- コマは **読み順（右→左、上→下）** に並べる。layouts.json のセルも同じ順

## 画像・入稿設定

`spec/style.json`

| キー | 既定 | 意味 |
| --- | --- | --- |
| gen_width / gen_height | 1024×1536 | 生成画像サイズ（2:3。セルの縦横比に合わせて cover 切り抜き） |
| page_width / page_height | 1200×1920 | 入稿ページサイズ（仕様書の推奨値。1600×2560 に上げる場合はここだけ変更） |
| font_size / font_size_small | 34 / 28 | セリフ / ナレーション・モノローグの文字サイズ（page 基準 px） |
| max_chars_per_column | 11 | 1段の最大文字数（吹き出しの縦長さ） |
| jpeg_quality | 88 | 出力 JPEG 品質 |

## KDP 登録時の注意（仕様書 §4 より）

- AI 生成コンテンツの申告で **「画像が AI 生成」** を選ぶ（加工していても対象）
- 右開き（`book.json` の `direction: rtl`）。EPUB 側で設定済み
- フォントは埋め込み・商用利用可のもの（`fonts/README.md`）
- ビルド後は Kindle Previewer で「スマホ縦」「タブレット横（見開き）」「Kindle 端末」を確認。
  KDP 一般のチェックリストは `../manga/docs/kdp-checklist.md`
