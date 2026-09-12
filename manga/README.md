# Kindle（KDP）向け マンガ制作キット

Amazon Kindle ダイレクト・パブリッシング（KDP）で電子コミックを出版するための、
**企画 → ネーム → 原稿 → 固定レイアウトEPUB → 入稿** までを1つのフォルダで管理するキットです。

```
manga/
├── README.md              ← このファイル（全体の流れ・仕様）
├── book.json              ← 作品メタデータ（タイトル・著者・ページサイズ・開き方向）
├── docs/
│   ├── story-plan.md      ← 企画シート（テーマ・キャラ・あらすじ）
│   ├── kdp-checklist.md   ← KDP入稿・出版チェックリスト
│   └── name/              ← ネーム（ページ台本）。1ページ1ファイル
├── pages/                 ← 本文原稿画像（p001.png, p002.png …）※ここに完成原稿を置く
├── cover/                 ← 表紙画像（cover.jpg）
├── templates/             ← 原稿用紙テンプレート（ガイド線付きPNG） ※tools/make_templates.py で生成
├── tools/
│   ├── make_templates.py  ← 原稿用紙テンプレ生成
│   ├── check_pages.py     ← 原稿の連番・サイズ・容量チェック
│   ├── prepare_pages.py   ← 原稿を入稿サイズに揃えて dist/pages に書き出し
│   ├── build_epub.py      ← 固定レイアウトEPUB3（右開き・見開き対応）を生成
│   └── render_pages.mjs   ← HTML/SVGで描いたページをPNG化（Playwright）
├── sample/                ← 4ページのサンプル短編（HTML/SVG原稿 → PNG → EPUB の動作確認用）
└── dist/                  ← 生成物（git管理外）
```

---

## 1. 制作の流れ

| 工程 | 何をするか | 使うもの |
| --- | --- | --- |
| ① 企画 | テーマ・ターゲット・キャラ・あらすじを決める | `docs/story-plan.md` |
| ② ネーム | 1ページごとにコマ割り・セリフ・構図を書く | `docs/name/p001.md` … |
| ③ 原稿 | 作画ツール（CLIP STUDIO PAINT、Procreate 等）で描く。テンプレを下敷きに | `templates/` |
| ④ 書き出し | `pages/` に `p001.png` … の連番で保存。表紙は `cover/cover.jpg` | — |
| ⑤ 検品 | 連番・サイズ・容量をチェック | `python3 tools/check_pages.py` |
| ⑥ 整形 | 入稿サイズに統一し JPEG/PNG を最適化 | `python3 tools/prepare_pages.py` |
| ⑦ EPUB化 | 右開き固定レイアウトEPUBを生成 | `python3 tools/build_epub.py` |
| ⑧ 確認 | **Kindle Previewer**（Amazon公式・無料）で開いて端末別表示を確認 | Windows / Mac |
| ⑨ 入稿 | KDPにEPUBと表紙をアップロード、メタデータ・価格を設定 | `docs/kdp-checklist.md` |

### クイックスタート（サンプルで動作確認）

```bash
cd manga
pip install pillow                       # 初回のみ
python3 tools/make_templates.py          # templates/ に原稿用紙テンプレを生成
bash sample/build.sh                     # サンプル原稿(HTML) → PNG → dist/sample.epub
```

`sample/build.sh` の中身は「render_pages.mjs でPNG化 → check_pages.py で検品 → build_epub.py でEPUB化」の3行です。

自分の作品を作るときは `pages/` と `cover/` に画像を置き、`book.json` を編集して

```bash
python3 tools/check_pages.py
python3 tools/prepare_pages.py
python3 tools/build_epub.py
```

`dist/<タイトル>.epub` が入稿ファイルです。

---

## 2. 画像仕様（このキットの既定値）

| 項目 | 既定値 | 補足 |
| --- | --- | --- |
| 本文ページ | **1600 × 2560 px**（縦横比 1:1.6） | Kindle Comic Creator 等で案内されている標準サイズ。スマホ〜タブレット〜Kindle端末までこれ1種で対応 |
| 見開き1枚絵 | 3200 × 2560 px | 横長画像を置くと自動で「見開き中央」扱い |
| 表紙 | **1600 × 2560 px**、JPEG | KDP表紙の推奨は縦横比 1.6:1、最小 625×1000、最大 10000 px、50MB 以下、RGB |
| 形式 | 本文 PNG または JPEG、表紙 JPEG/TIFF | モノクロ原稿はグレースケールPNGが軽くて綺麗、カラーはJPEG品質90前後 |
| 1画像の容量 | 5 MB 以下 | KDPの画像あたり上限。`check_pages.py` が警告します |
| 全体 | 650 MB 以下 | KDPのアップロード上限 |
| 解像度 | 300dpi 相当で作画 → 上記pxに縮小 | 作画は大きめ（例：B5 350dpi）で、書き出し時に縮小がおすすめ |
| 開き方向 | **右開き**（日本のマンガ標準） | `book.json` の `"direction": "rtl"` |
| ページ配置 | 表紙＝単独、1ページ目＝左、2ページ目＝右 … | 日本の書籍慣習（奇数ページが左）。`first_page_side` で変更可 |

> **注意**: 上記の数値は KDP ヘルプ（表紙ガイドライン / 固定レイアウト / 画像フォーマット）の
> 公開情報と業界慣行に基づく 2026年9月時点の値です。入稿前に KDP ヘルプの最新版で必ず再確認してください。
> - 表紙ガイドライン: https://kdp.amazon.co.jp/ja_JP/help/topic/G6GTK3T3NUHKLEFX
> - 固定レイアウト本（コミック）: https://kdp.amazon.co.jp/ja_JP/help/topic/G9GSTY4LTRT39D4Z
> - 本の画像のフォーマット: https://kdp.amazon.co.jp/ja_JP/help/topic/G202169030

### 原稿用紙テンプレートのガイド線

`tools/make_templates.py` が生成する PNG には次のガイドが入っています。

- **仕上がり枠**（外周）：1600×2560 の全面。
- **セーフエリア**（内側 約5%）：セリフ・重要な絵はこの中に。端末によっては端がわずかに切れる／UIに隠れる。
- **基本枠（内枠）**：紙のマンガでいうコマ配置の基準枠。
- **ノド側マーク**：見開き表示のとき中央に来る側（左ページは右辺、右ページは左辺）。

---

## 3. 作画データの作り方（CLIP STUDIO PAINT の例）

1. 新規キャンバス：幅 1600 × 高さ 2560 px、解像度 350dpi（px指定なら dpi は表示用）。
   もしくは B5 原稿用紙（同人誌設定）で描き、書き出し時に「高さ 2560px」に縮小。
2. `templates/page_template.png` を最下層レイヤーに読み込み、不透明度を下げて下敷きに。
3. 完成したら「画像を統合して書き出し」→ PNG（モノクロ二階調 or グレースケール）／JPEG（カラー）。
4. ファイル名は `p001.png` のように **3桁ゼロ埋め連番**。見開き1枚絵は `p010-011.png` のように範囲名にすると分かりやすい（横長なら自動判定）。

---

## 4. EPUB の中身（build_epub.py が生成するもの）

- EPUB 3 固定レイアウト（`rendition:layout = pre-paginated`）
- 右開き（`page-progression-direction="rtl"`）
- 見開き制御（`rendition:spread = landscape`、各ページに `page-spread-left / right`、表紙・横長画像は `center`）
- Kindle 向け互換メタ（`fixed-layout`, `original-resolution`, `book-type: comic`, `primary-writing-mode: horizontal-rl`）
- 目次（nav.xhtml）：表紙・本文開始・`book.json` の `chapters` に書いた区切り

生成後は **Kindle Previewer** で開き、「スマホ縦」「タブレット横（見開き）」「Kindle端末」の3種で確認してください。

---

## 5. 出版まで

`docs/kdp-checklist.md` を上から順に。要点だけ：

- KDPアカウント（税務情報・銀行口座）→ 本の詳細（タイトル・著者名・内容紹介・キーワード7つ・カテゴリー）→ 原稿と表紙 → 価格（KDPセレクト加入で読み放題対象、70%ロイヤリティは 250〜1,250円等の条件あり）
- 審査は通常 72 時間以内。コミックは「固定レイアウト」で申請。
- 表紙のテキストは表紙画像に焼き込む（サムネイルで読めるサイズに）。

---

## 6. 依存ツール

- Python 3.9+ と `pillow`（`pip install pillow`）
- Node.js 18+ と `playwright`（サンプルの HTML → PNG 化のみ。手描き原稿を使うなら不要）
- Kindle Previewer 3（表示確認用、Amazon公式・無料）
- （任意）epubcheck（EPUB 構文チェック）
