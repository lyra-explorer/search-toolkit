# search-toolkit

**目的**: ターミナルから自分のファイルを楽に探すためのツール。

## インストール済み

`~/bin/se` にリンク済み。どこからでも `se` で呼べる。

## 使い方

### 基本的なローマ字検索

```
$ se nemusou
D:\data\Pi-Coding-Fun\...\ねむそう.webp
D:\data\Pi-Coding-Fun\...\ねむそう２.jpg
```

ローマ字で打つと自動で日本語に展開して Everything で検索する。
`nemusou` → `(ねむそう|ｎｅｍｕｓｏｕ|nemusou)` に変換される。

### 日本語で直接検索

```
$ se ねむそう
```

日本語が含まれていれば migemo を通さずにそのまま検索。

### 件数を絞る

```
$ se -n 5 nemusou
```

### パスを限定する

```
$ se -p "D:\data\Pi-Coding-Fun\Zundamon-Videos" mp4
```

指定しない場合は `D:\data\Pi-Coding-Fun` 全体を検索。

### fzf で絞り込む

```
$ se -f mp4
```

検索結果が fzf で開く。`bat` でプレビュー付き。Enter で選択。

### migemo の展開結果だけ見る

```
$ se -e kawaii
(かわいい|ｋａｗａｉｉ|kawaii)
```

検索はしない。正規表現の確認用。

### migemo なしでそのまま渡す

```
$ se -- ext:png;jpg
```

Everything の構文を直接使いたい時。

## どう便利になるか

| これまで | se を使うと |
|---------|-----------|
| `es ねむそう` （日本語入力モードに切り替えて入力） | `se nemusou` （ローマ字のまま） |
| ファイル名を正確に覚えてないとヒットしない | `kawaii` で `かわいい` を含むファイルが全部出る |
| Everything の構文を覚える必要がある | `se` + ローマ字だけでいい |

## 中身

```
src/se.py    — Python スクリプト（pymigemo + es.exe）
src/se       — Git Bash / WezTerm 用ラッパー
src/se.cmd   — PowerShell / cmd 用ラッパー
```

## 依存（すべてインストール済み）

| コンポーネント | 役割 | バージョン・場所 |
|--------------|------|-----------------|
| **Python 3.12** | se.py の実行環境 | `C:\Users\class\AppData\Local\Programs\Python\Python312\` |
| **pymigemo** | ローマ字→日本語正規表現展開。純Python実装で辞書内蔵。cmigemo.dll 不要 | `pip install pymigemo` (0.0.1) |
| **Everything** | NTFS USN Journal ベースのファイル名インデックスエンジン。常駐サービス | [voidtools.com](https://www.voidtools.com/) |
| **es.exe** | Everything の CLI フロントエンド。`-r` で正規表現検索 | `C:\Program Files\Everything\es.exe` (1.1.0.30) |
| **fzf** | 検索結果のインタラクティブ絞り込み（`-f` 時のみ使用） | WinGet (0.72.0) |
| **bat** | fzf プレビューでのファイル内容表示（`-f` 時のみ使用） | WinGet (0.26.1) |

## 処理フロー

```
入力: se nemusou
  │
  ├─ 日本語文字を含む？
  │    ├─ No → pymigemo で展開
  │    │       nemusou → (ねむそう|ｎｅｍｕｓｏｕ|nemusou)
  │    └─ Yes → そのまま
  │
  ├─ es.exe -r "正規表現" -path "D:\data\Pi-Coding-Fun"
  │
  └─ -f オプション？
       ├─ Yes → fzf --preview 'bat {}' で絞り込み
       └─ No → 標準出力に一覧
```

### pymigemo がやっていること

入力されたローマ字を、ひらがな・カタカナ・半角カナ・ローマ字の組み合わせ正規表現に展開する。
辞書ファイル（`migemo-compact-dict`）がパッケージに同梱されており、C拡張や外部dllは不要。

```
nemusou → (ねむそう|ｎｅｍｕｓｏｕ|nemusou)
kawaii  → (かわいい|ｋａｗａｉｉ|kawaii)
kusa    → (くさ|ｋｕｓａ|草|kusa)
```

### Everything (es.exe) がやっていること

Windows の NTFS USN Journal を利用してファイル名インデックスを常時構築。
es.exe はその IPC クライアントで、`-r` オプションで正規表現検索を投げる。
フルスキャン不要で数百万ファイルから一瞬で結果を返す。

### fzf + bat がやっていること（`-f` 時のみ）

es の結果をパイプで fzf に流し込み、インクリメンタル絞り込み。
bat でファイル内容のシンタックスハイライトプレビューを表示。
