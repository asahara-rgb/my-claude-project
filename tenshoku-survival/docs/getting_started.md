# はじめてのかたへ：第1話を作るまでの手順（プログラミング不要版あり）

いま止まっているのは「**キャラの絵を AI で 20 枚くらい試しに描かせて、毎回同じ顔になるか確かめる**」工程です。
これに合格したら第1話 36 コマの絵を作り、あとは自動でページとEPUBになります。

やり方は 2 つ。**まずは A（手作業）で十分です。**

---

## A. 手作業でやる（ターミナル不要・30〜60分）

用意するもの：Gemini のアプリまたは Web（無料枠で可。画像生成ができるモード）。ChatGPT でも同じ手順で可。

### A-1. キャラの「見本」を作る（各キャラ 2 枚）

1. GitHub のこのフォルダ `tenshoku-survival/raw/refs/` を開き、`yota_prompts.txt` を開く。
2. 中の英文（2 つあります）を **1 つずつ** Gemini に貼り付けて画像を作らせる。
   - 1 つ目＝正面・横・斜めの三面図、2 つ目＝表情 6 種のシート。
3. 気に入らなければ「もう一度」を何回でも。**この 2 枚がこの先すべての絵の基準になる**ので、
   髪型・眼鏡・服が設定どおりで、顔が好みのものを選ぶ。
4. 選んだ画像を保存して、ファイル名を `yota_1.png`（三面図）、`yota_2.png`（表情）にする。
5. `rei_prompts.txt` でも同じことをして `rei_1.png`, `rei_2.png` を作る。

### A-2. 20 通りの構図で描かせて、同じ人に見えるか確かめる

1. 同じ Gemini の会話に **A-1 で選んだ 2 枚の画像を添付**し、
   「添付画像をキャラクターの参照シートとして、顔・髪・服を完全に同じにして描いてください」と一言添える。
2. `raw/test/yota_prompts.txt` の 01〜20 の英文を 1 つずつ貼って生成する（全部でなくても、10 枚でも目安になる）。
3. できた画像を保存し `yota_01.png` … `yota_20.png` と名前を付ける。玲（rei）も同じ。

### A-3. 判定

- 20 枚のうち **16 枚以上が同じ人物に見える** → 合格。第1話の絵の生成に進む（A-4）。
- 12〜15 枚 → 見本 2 枚を選び直してもう一度。
- 12 枚未満 → この方法では厳しいので、別の手段（LoRA 学習・外注）を検討。

判断に迷ったら、できた画像をこのチャットにまとめて貼ってください。こちらで見て判定します。

### A-4. 第1話のコマを描かせる

1. `raw/ep01/` に `p01_c01.txt` 〜 `p10_c03.txt` の **36 個のプロンプト**があります。
2. A-2 と同じく見本 2 枚を添付した状態で、1 つずつ貼って生成。1 コマにつき 2〜4 枚作って気に入ったものを選ぶ。
3. 選んだ画像を `p01_c01_a.png` のように **「プロンプトのファイル名 ＋ _a」** の名前で保存する。
   36 枚そろったら zip にしてこのチャットに送るか、GitHub の `tenshoku-survival/raw/ep01/` にアップロードしてください。
4. その先（吹き出し合成・ページ組み・EPUB 化）はこちらで実行して、完成 EPUB をお渡しします。

---

## B. 自分のパソコンで自動実行する（ターミナルを使う）

慣れてきたら。A を 1,500 枚ぶん手でやるのは大変なので、第2話以降はこちらに切り替えるのがおすすめです。

1. **Python をインストール**（python.org から 3.11 以上）。
2. **このリポジトリを取得**：GitHub で「Code → Download ZIP」または `git clone`。ブランチは `claude/amazon-kindle-manga-2j3shb`。
3. **API キーを取得**：Google AI Studio（aistudio.google.com）で「Get API key」。有料枠にすると 1 枚あたり数円〜十数円。
4. ターミナル（Mac は「ターミナル」、Windows は「PowerShell」）で：
   ```bash
   cd tenshoku-survival
   pip install pillow
   export GEMINI_API_KEY=ここにキー          # Windows PowerShell は  $env:GEMINI_API_KEY="ここにキー"

   python3 scripts/00_character_test.py sheet --provider gemini --dry-run   # 送る内容を表示するだけ（お金はかからない）
   python3 scripts/00_character_test.py sheet --provider gemini             # 見本を作る → raw/refs/
   python3 scripts/00_character_test.py test  --provider gemini --count 20  # 20 構図 → raw/test/
   python3 scripts/00_character_test.py sheet-view                          # 一覧画像 raw/test/contact_yota.png を見る
   ```
5. 合格なら第1話：
   ```bash
   python3 scripts/01_gen_images.py --episode 1 --provider gemini --variants 4   # 36コマ × 4案
   #   raw/ep01/ を見て、採用したい案（a〜d）を spec/ep01/pages.json の各コマに "pick": "b" のように書く
   python3 scripts/03_build_pages.py --episode 1 --preview      # composed/ep01/ に確認用PNG
   python3 scripts/03_build_pages.py --episode 1                # build/pages/ に本番JPEG
   python3 scripts/05_build_cover.py --art （表紙用に選んだ画像）
   python3 scripts/04_build_epub.py                             # build/tenshoku-survival.epub
   ```
6. エラーが出たら、赤い文字をそのままこのチャットに貼ってください。API まわりは未検証なので初回はエラーが出る可能性があります。

---

## 用語

| 用語 | 意味 |
| --- | --- |
| プロンプト | AI に渡す「こういう絵を描いて」という英文。すでに全部書いてあります |
| 参照画像（見本） | 「この人と同じ顔で」と一緒に渡す画像。一貫性の要 |
| API キー | プログラムから AI を呼ぶための合言葉。Web 画面で手動でやるなら不要 |
| EPUB | 電子書籍のファイル形式。KDP にはこれをアップロードします |
| Kindle Previewer | Amazon 公式の無料ソフト。EPUB を Kindle でどう見えるか確認する（Windows / Mac） |
