"""
RSS フィードから記事を収集するモジュール
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import feedparser
import requests

logger = logging.getLogger(__name__)


def fetch_rss_articles(
    source_name: str,
    url: str,
    days_lookback: int = 7,
    max_articles: int = 10,
    timeout: int = 10,
) -> list[dict]:
    """
    RSSフィードから記事を取得する

    Args:
        source_name: ソース名（ログ用）
        url: RSSフィードのURL
        days_lookback: 何日前までの記事を取得するか
        max_articles: 最大取得件数
        timeout: タイムアウト秒数

    Returns:
        記事のリスト [{"title": ..., "url": ..., "summary": ..., "published": ...}]
    """
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_lookback)

    try:
        # feedparser は requests で取得してから渡す（タイムアウト制御のため）
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "SP-News-Update/1.0"})
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except requests.RequestException as e:
        logger.warning(f"[{source_name}] フェッチ失敗: {e}")
        return []
    except Exception as e:
        logger.warning(f"[{source_name}] パース失敗: {e}")
        return []

    for entry in feed.entries[:max_articles * 2]:  # 日付フィルタ後に max_articles に絞るため多めに取得
        try:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()

            # HTMLタグを簡易除去
            import re
            summary = re.sub(r"<[^>]+>", "", summary)
            summary = summary[:500]  # 長すぎる場合は切り詰め

            # 公開日時のパース
            published = _parse_published(entry)

            # 日付フィルタ（公開日が取得できない場合は含める）
            if published and published < cutoff:
                continue

            if title and link:
                articles.append({
                    "source": source_name,
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "published": published.isoformat() if published else None,
                })

            if len(articles) >= max_articles:
                break

        except Exception as e:
            logger.debug(f"[{source_name}] エントリ処理エラー: {e}")
            continue

    logger.info(f"[{source_name}] {len(articles)} 件取得")
    return articles


def _parse_published(entry) -> Optional[datetime]:
    """feedparserエントリから公開日時をパースする"""
    import time
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(field)
        if value:
            try:
                return datetime(*value[:6], tzinfo=timezone.utc)
            except Exception:
                continue
    return None
