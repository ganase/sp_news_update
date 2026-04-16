# SP News Update

専門領域（セキュリティ・AI・ヘルプデスク）の最新情報を収集・AI要約してメール配信するシステム。

## ディレクトリ構成

```
sp_news_update/
├── config.yaml          # 全設定（APIキー・SMTP・スケジュール・ドメイン）
├── main.py              # メインスクリプト
├── scheduler.py         # スケジューラー（常駐プロセス）
├── requirements.txt     # 依存パッケージ
├── collectors/
│   └── rss_collector.py # RSS記事収集
├── writer/
│   └── ai_writer.py     # Rakuten AI による記事生成
├── mailer/
│   └── sender.py        # メール送信
├── prompts/             # ドメインごとのAIプロンプト
│   ├── security.yaml
│   ├── ai_data.yaml
│   └── helpdesk.yaml
├── templates/
│   └── email.html       # メールHTMLテンプレート
└── logs/                # ログ・プレビューHTML出力先
```

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. config.yaml の設定

`config.yaml` を開き、以下を実際の値に変更してください：

| 設定項目 | 説明 |
|---|---|
| `ai.api_key` | Rakuten AI の APIキー |
| `mail.smtp_host` | SMTPサーバーのホスト名 |
| `mail.smtp_user` | 送信元メールアドレス |
| `mail.smtp_password` | SMTPパスワード |
| `mail.from_address` | 送信元アドレス |
| `mail.to_address` | 配信先メーリングリストアドレス |

## 使い方

### ドライラン（メール送信なし・動作確認用）

```bash
python main.py --dry-run
```

`logs/preview_YYYY年MM月DD日.html` にプレビューHTMLが出力されます。

### 通常実行（メール送信あり）

```bash
python main.py
```

### スケジューラー起動（毎週月曜8時に自動実行）

```bash
python scheduler.py
```

### スケジューラー即時実行テスト

```bash
python scheduler.py --now --dry-run
```

## 新しいドメインの追加方法

1. `prompts/` に新しいプロンプトファイルを作成（例: `it_infra.yaml`）
2. `config.yaml` の `domains` に新しいエントリを追加：

```yaml
- id: "it_infra"
  name: "ITインフラ"
  active: true
  prompt_file: "it_infra.yaml"
  sources:
    - name: "ソース名"
      url: "https://example.com/feed.rss"
      type: "rss"
```

## Windows タスクスケジューラでの常駐化

`scheduler.py` を常駐させる代わりに、Windows タスクスケジューラに登録することもできます。

1. タスクスケジューラを開く
2. 「基本タスクの作成」→ 毎週月曜 08:00 に設定
3. 操作: `python C:\Users\...\sp_news_update\main.py`
