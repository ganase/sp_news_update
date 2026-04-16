# SP News Update

## このシステムは何をするものか

セキュリティ・AI・ヘルプデスクといった専門領域の最新ニュースを、インターネット上のRSSフィードから自動収集し、AIが社員向けにわかりやすく要約・記事化して、毎週月曜日の朝8時にメーリングリストへ自動配信するシステムです。

**専門知識がなくても重要情報が届く仕組み**を、継続的に・自動で回し続けることを目的としています。

---

## なぜこのシステムを作ったか（背景と課題）

セキュリティやAI・ヘルプデスクといった専門領域は、一般社員にも影響が大きく、かつ情報の鮮度が重要です。しかし現状では：

- 専門分野への関心や知識がないと、自ら情報収集するのが難しい
- 必要な情報を探して理解するのに時間がかかる
- その結果、対応が後手に回ることが多い

このシステムは、**AIが情報収集・要約を自動で行い、人間は品質確認だけに集中できる**構造を実現します。

---

## 誰が何をするか（役割分担）

このシステムには3つの役割があります。

### 1. システム管理者（IT担当）
- 初回のセットアップ・サーバー設定
- APIキーやメール設定の管理
- スケジューラーの起動・監視

### 2. 領域専門家（**非IT担当者も担当できます**）
- 自分の担当領域のプロンプトファイル（`prompts/` フォルダ内）を編集・管理
- 新しい情報源（RSSフィードURL）の追加
- 配信内容の品質チェック・フィードバック
- **プログラムの知識は不要です。YAMLファイルの編集のみです。**

### 3. 読者（一般社員）
- 毎週月曜朝8時にメールを受け取るだけ
- 重要な情報は「社員へのアクション」として明示されています

---

## ファイルの役割一覧

```
sp_news_update/
│
├── config.yaml          ← 【重要・非公開】APIキー・メール設定・スケジュール
├── config.yaml.example  ← config.yaml のひな型（GitHubに公開されている）
├── .gitignore           ← GitHubに公開しないファイルのリスト
│
├── main.py              ← システムの司令塔。収集→生成→送信を順番に実行
├── scheduler.py         ← 毎週月曜8時に main.py を自動実行するタイマー
├── requirements.txt     ← 必要なPythonライブラリの一覧
│
├── collectors/
│   └── rss_collector.py ← インターネットのRSSフィードから記事を収集
│
├── writer/
│   └── ai_writer.py     ← Rakuten AIを呼び出して記事HTMLを生成
│
├── mailer/
│   └── sender.py        ← 生成したHTMLをメールで送信
│
├── prompts/             ← 【専門家が編集する場所】領域ごとのAI指示書
│   ├── security.yaml    ← セキュリティ領域の指示書
│   ├── ai_data.yaml     ← AI・DATA領域の指示書
│   └── helpdesk.yaml    ← ヘルプデスク領域の指示書
│
├── templates/
│   └── email.html       ← メールのデザインテンプレート
│
└── logs/                ← 実行ログとプレビューHTMLの保存場所
```

---

## config.yaml と .gitignore の役割と、なぜ分けているか

### config.yaml とは

システムを動かすための**秘密情報・環境固有の設定**をまとめたファイルです。

```yaml
ai:
  api_key: "実際のAPIキー"      ← 絶対に外部に漏らしてはいけない情報

mail:
  smtp_password: "パスワード"   ← 同上
  to_address: "社内メーリングリスト"
```

このファイルは**各自のPC上にだけ存在します**。GitHubには絶対にアップロードしません。

### .gitignore とは

GitHubへのアップロード（push）から**除外するファイル・フォルダを指定するリスト**です。

```.gitignore
config.yaml   ← これがあることで、config.yaml は自動的に無視される
logs/         ← ログファイルも除外
```

> **なぜ分けるのか**
>
> GitHubはコードを共有・管理する場所ですが、**パブリックリポジトリのファイルはインターネット上の誰でも見ることができます**。APIキーやパスワードを誤って公開すると、第三者に悪用されるリスクがあります。
>
> そこで「設定のひな型」である `config.yaml.example` だけをGitHubに置き、実際の秘密情報を含む `config.yaml` は `.gitignore` によって公開されないよう保護しています。
>
> | ファイル | GitHub公開 | 内容 |
> |---|---|---|
> | `config.yaml.example` | 公開する | 空欄・ダミー値のひな型 |
> | `config.yaml` | **公開しない** | 実際のAPIキー・パスワード |
> | `.gitignore` | 公開する | 公開除外リスト |

---

## 領域専門家向け：プロンプトの編集方法

プロンプトファイルとは、**AIへの指示書**です。「どんな観点で記事を要約するか」「読者に何を伝えるか」を自然な文章で記述します。プログラムの知識は不要です。

### ファイルの場所

```
prompts/
├── security.yaml    ← セキュリティ担当者が編集
├── ai_data.yaml     ← AI・DATA担当者が編集
└── helpdesk.yaml    ← ヘルプデスク担当者が編集
```

### プロンプトファイルの構造

```yaml
domain_name: "セキュリティ"

system_prompt: |
  ここにAIへの基本的な役割・姿勢を書く。
  例：「専門用語は平易な言葉で説明する」
      「対応が必要な場合は具体的なアクションを示す」

article_prompt: |
  収集した記事一覧を渡したときに、AIにどう加工させるかを書く。
  出力のHTML形式もここで指定する。
```

### 新しい情報源（RSSフィード）を追加する

`config.yaml` の該当ドメインの `sources` に1行追加するだけです。

```yaml
- name: "追加したいサイト名"
  url: "https://example.com/feed.rss"
  type: "rss"
```

> RSSフィードのURLが分からない場合は、対象サイトで `RSS` や `フィード` と検索するか、URLの末尾に `/feed` や `/rss` を試してみてください。

---

## 新しい専門領域を追加する手順

たとえば「法務・コンプライアンス」領域を追加したい場合：

**Step 1：プロンプトファイルを作成**

`prompts/compliance.yaml` を作成し、`security.yaml` を参考に内容を記述します。

**Step 2：config.yaml にドメインを追加**

```yaml
domains:
  - id: "compliance"
    name: "法務・コンプライアンス"
    active: true
    prompt_file: "compliance.yaml"
    sources:
      - name: "情報源サイト名"
        url: "https://example.com/feed.rss"
        type: "rss"
```

**Step 3：動作確認**

```bash
python main.py --dry-run
```

`logs/` フォルダにプレビューHTMLが出力されるので、ブラウザで開いて内容を確認します。

---

## セットアップ手順（初回のみ・IT担当者向け）

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. config.yaml の作成

```bash
cp config.yaml.example config.yaml
```

`config.yaml` を開いて以下を設定してください：

| 設定項目 | 説明 |
|---|---|
| `ai.api_key` | Rakuten AI の APIキー |
| `mail.smtp_host` | SMTPサーバーのホスト名 |
| `mail.smtp_user` | 送信元メールアドレス |
| `mail.smtp_password` | SMTPパスワード |
| `mail.from_address` | 送信元アドレス |
| `mail.to_address` | 配信先メーリングリストアドレス |

### 3. 動作確認（ドライラン）

```bash
python main.py --dry-run
```

メールは送信されず、`logs/preview_YYYY年MM月DD日.html` にプレビューが出力されます。ブラウザで開いて内容を確認してください。

### 4. 自動実行の設定

**方法A：スケジューラーを常駐させる**

```bash
python scheduler.py
```

**方法B：Windowsタスクスケジューラに登録する**

1. 「タスクスケジューラ」を開く
2. 「基本タスクの作成」→ 毎週月曜 08:00 を設定
3. 操作に `python C:\Users\...\sp_news_update\main.py` を指定

---

## 処理の流れ

```
毎週月曜 08:00
      ↓
[scheduler.py] タイマー起動
      ↓
[main.py] 全ドメインをループ処理
      ↓
[collectors/rss_collector.py] RSSフィードから記事を収集（過去7日分）
      ↓
[writer/ai_writer.py] Rakuten AIに記事一覧を渡して要約・HTML生成
      ↓
[mailer/sender.py] メーリングリストへHTMLメールを送信
      ↓
[logs/] 実行ログ・プレビューHTMLを保存
```
