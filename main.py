"""
SP News Update - メインエントリーポイント

使い方:
  python main.py          # 通常実行（メール送信あり）
  python main.py --dry-run  # ドライラン（HTMLファイル出力のみ、メール送信なし）
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from collectors.rss_collector import fetch_rss_articles
from writer.ai_writer import create_writer_from_config
from mailer.sender import MailSender, build_email_html

# ログ設定
def setup_logging():
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

logger = logging.getLogger(__name__)


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompt(prompt_file: str) -> dict:
    prompt_path = Path(__file__).parent / "prompts" / prompt_file
    with open(prompt_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_preview(html: str, issue_date: str):
    """プレビュー用HTMLをファイルに保存する"""
    preview_dir = Path(__file__).parent / "logs"
    preview_dir.mkdir(exist_ok=True)
    preview_file = preview_dir / f"preview_{issue_date.replace(' ', '_')}.html"
    preview_file.write_text(html, encoding="utf-8")
    logger.info(f"プレビューHTML保存: {preview_file}")
    return preview_file


def run(dry_run: bool = False):
    setup_logging()
    logger.info("=" * 60)
    logger.info("SP News Update 開始")
    logger.info(f"モード: {'ドライラン（メール送信なし）' if dry_run else '通常実行'}")
    logger.info("=" * 60)

    config = load_config()
    ai_cfg = config["ai"]
    mail_cfg = config["mail"]
    collection_cfg = config["collection"]
    domains_cfg = config["domains"]

    # AI ライター初期化（config.yaml の ai.provider で自動切り替え）
    writer = create_writer_from_config(ai_cfg)
    logger.info(f"AIプロバイダー: {ai_cfg.get('provider', 'rakuten')}")

    issue_date = datetime.now().strftime("%Y年%m月%d日")
    all_sections_html = []

    # ドメインごとに処理
    for domain in domains_cfg:
        if not domain.get("active", False):
            logger.info(f"[{domain['id']}] スキップ（active=false）")
            continue

        domain_name = domain["name"]
        logger.info(f"--- ドメイン処理開始: {domain_name} ---")

        # 記事収集
        all_articles = []
        for source in domain.get("sources", []):
            if source["type"] == "rss":
                articles = fetch_rss_articles(
                    source_name=source["name"],
                    url=source["url"],
                    days_lookback=collection_cfg["days_lookback"],
                    max_articles=collection_cfg["max_articles_per_domain"],
                    timeout=collection_cfg["fetch_timeout_seconds"],
                )
                all_articles.extend(articles)

        logger.info(f"[{domain_name}] 合計 {len(all_articles)} 件の記事を収集")

        if not all_articles:
            logger.warning(f"[{domain_name}] 記事が取得できませんでした。このドメインはスキップします。")
            all_sections_html.append(
                f'<div class="domain-section"><h2>{domain_name}</h2>'
                f'<p class="no-articles">今週は収集できた記事がありませんでした。</p></div>'
            )
            continue

        # プロンプト読み込み
        try:
            prompt_data = load_prompt(domain["prompt_file"])
        except FileNotFoundError:
            logger.error(f"[{domain_name}] プロンプトファイルが見つかりません: {domain['prompt_file']}")
            continue

        # AI で記事生成
        section_html = writer.generate_domain_section(
            system_prompt=prompt_data["system_prompt"],
            article_prompt_template=prompt_data["article_prompt"],
            articles=all_articles,
        )

        if section_html:
            all_sections_html.append(section_html)
            logger.info(f"[{domain_name}] HTML生成完了")
        else:
            logger.error(f"[{domain_name}] HTML生成失敗")
            all_sections_html.append(
                f'<div class="domain-section"><h2>{domain_name}</h2>'
                f'<p class="no-articles">記事の生成に失敗しました。</p></div>'
            )

    if not all_sections_html:
        logger.error("全ドメインで記事生成に失敗しました。処理を終了します。")
        sys.exit(1)

    # メールHTML構築
    full_html = build_email_html(
        domain_sections_html="\n\n".join(all_sections_html),
        issue_date=issue_date,
        year=datetime.now().strftime("%Y"),
        from_address=mail_cfg["from_address"],
    )

    # プレビュー保存（常に実施）
    preview_file = save_preview(full_html, issue_date)
    logger.info(f"プレビュー確認: {preview_file}")

    if dry_run:
        logger.info("ドライランモード: メール送信をスキップしました")
        logger.info(f"生成されたHTMLは {preview_file} で確認できます")
        return

    # メール送信
    mail_sender = MailSender(
        smtp_host=mail_cfg["smtp_host"],
        smtp_port=mail_cfg["smtp_port"],
        smtp_user=mail_cfg["smtp_user"],
        smtp_password=mail_cfg["smtp_password"],
        use_tls=mail_cfg["use_tls"],
        from_address=mail_cfg["from_address"],
        from_name=mail_cfg["from_name"],
    )

    subject = f"【SP News Update】{issue_date}号 - セキュリティ・AI・ヘルプデスク最新動向"
    success = mail_sender.send(
        to_address=mail_cfg["to_address"],
        subject=subject,
        html_body=full_html,
    )

    if success:
        logger.info("メール送信完了")
    else:
        logger.error("メール送信に失敗しました")
        sys.exit(1)

    logger.info("SP News Update 正常終了")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SP News Update")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="メール送信せずにHTMLプレビューのみ生成する",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
