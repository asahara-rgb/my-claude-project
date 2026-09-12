# fonts/

セリフ合成（`scripts/02_compose_text.py`）で使う日本語フォントをここに置く。
**電子書籍への埋め込み・商用利用が許可されたフォント**のみ使うこと。

推奨（無料・商用可・埋め込み可）:

- Noto Sans JP（SIL OFL）… 標準的なゴシック。`NotoSansJP-Regular.otf` と `NotoSansJP-Bold.otf` を置く
- 源暎アンチック / 源暎ぽっぷる（SIL OFL）… 漫画のセリフ向け（かな明朝＋漢字ゴシックの「アンチック体」）
- IPAexゴシック（IPAフォントライセンス）

ファイル名に `Bold` / `Black` / `W6` などが含まれるものは太字（**強調**）用として自動選択される。
何も置かない場合はシステムの Noto Sans CJK / IPAゴシック を探す。
