# 検索系CLIツール チートシート

## es (Everything CLI)

Everything のコマンドライン版。NTFSインデックスで瞬時検索。

```bash
es ねむそう                    # 名前で検索
es *.webp                       # 拡張子で検索
es -path "C:\Users\class\Desktop" *.jpg  # パス指定
es -regex "ねむそう\d*"         # 正規表現
es -s                           # ソート順変更
es -n 20                        # 結果数制限
```

- **速さ**: NTFSのUSN Journalベース。数百万ファイルでも<1秒
- **制限**: ファイル名のみ。中身は検索できない
- **日本語**: ひらがな・カタカナ・漢字はそのまま入力。ローマ字→かな変換はなし

## fd

find の高速版。並列走査。

```bash
fd "ねむそう"                   # 名前で検索
fd -e md                        # 拡張子指定
fd --type f                     # ファイルのみ
fd --type d                     # ディレクトリのみ
fd -d 3 "config"                # 深さ制限
fd -x rm {}                     # 検索結果にコマンド実行（注意）
```

- **速さ**: 並列I/Oで find より数倍速い
- **特徴**: デフォルトで .gitignore を尊重する

## rg (ripgrep)

超高速テキスト検索。中身で探す時はこれ。

```bash
rg "ねむそう"                   # テキスト検索
rg -i "README"                  # 大文字小文字無視
rg -t py "import"               # Pythonファイルのみ
rg -g "*.md" "##"               # globフィルタ
rg -l "pattern"                 # ファイル名のみ出力
rg -c "TODO"                    # マッチ数のみ
```

- **速さ**: SIMD + メモリマップで圧倒的
- **特徴**: デフォルトで .gitignore を尊重、隠しファイルを無視

## fzf

インタラクティブあいまい絞り込み。パイプで使う。

```bash
es *.jpg | fzf                  # Everythingの結果を絞り込み
fd | fzf --preview 'cat {}'     # fdの結果をプレビュー付きで
history | fzf                   # コマンド履歴検索
cat file.txt | fzf              # テキスト行の絞り込み
fzf -f "nemu"                   # 非インタラクティブフィルタ
```

- **キーバインド**: `Ctrl+T` ファイル選択, `Ctrl+R` 履歴検索
- **プレビュー**: `--preview` でファイルの中身を表示

## cmigemo

ローマ字 → 日本語正規表現 変換ツール。

```bash
cmigemo -q "nemusou"            # ローマ字→正規表現を出力
```

出力例: `(ねむそう|ネムソウ|寝そう|ねむソウ|ネムそう|...)`

### es と組み合わせる

```bash
es -regex "$(cmigemo -q 'nemusou')"
```

これで `nemusou` → 日本語正規表現 → Everything で hit。

- **仕組み**: 辞書ベースでローマ字→ひらがな→カタカナ→漢字の候補を列挙
- **前提**: cmigemo のインストールと辞書ファイルが必要

## 組み合わせパターン

```bash
# ローマ字でファイル探す
es -regex "$(cmigemo -q 'nemu')" | fzf

# 中身で探してファイル名で絞り込む
rg -l "delegate_task" | fzf --preview 'bat --style=numbers --color=always {}'

# ディレクトリ内の画像を全部見つける
fd -e jpg -e png -e webp | fzf --preview 'chafa {}'
```
