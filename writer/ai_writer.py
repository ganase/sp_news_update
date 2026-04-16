"""
Rakuten AI (OpenAI互換) を使って記事HTMLを生成するモジュール
"""
import json
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class AIWriter:
    def __init__(self, endpoint: str, api_key: str, model: str, max_tokens: int = 4096, temperature: float = 0.3):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate_domain_section(
        self,
        system_prompt: str,
        article_prompt_template: str,
        articles: list[dict],
    ) -> Optional[str]:
        """
        記事リストからドメインセクションのHTMLを生成する

        Args:
            system_prompt: システムプロンプト
            article_prompt_template: {articles} プレースホルダーを含むプロンプト
            articles: 収集した記事リスト

        Returns:
            生成されたHTML文字列、失敗時はNone
        """
        if not articles:
            logger.warning("記事が0件のため生成をスキップします")
            return None

        # 記事一覧をテキスト化
        articles_text = self._format_articles(articles)
        user_prompt = article_prompt_template.replace("{articles}", articles_text)

        try:
            response = requests.post(
                f"{self.endpoint}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            logger.info(f"AI生成完了 (tokens: {data.get('usage', {}).get('total_tokens', '?')})")
            return content

        except requests.RequestException as e:
            logger.error(f"AI API呼び出しエラー: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"レスポンス: {e.response.text[:500]}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"AI APIレスポンス解析エラー: {e}")
            return None

    def _format_articles(self, articles: list[dict]) -> str:
        """記事リストをAIへ渡すテキスト形式に変換する"""
        lines = []
        for i, a in enumerate(articles, 1):
            lines.append(f"[{i}]")
            lines.append(f"  タイトル: {a.get('title', '')}")
            lines.append(f"  URL: {a.get('url', '')}")
            lines.append(f"  出典: {a.get('source', '')}")
            if a.get("published"):
                lines.append(f"  公開日: {a.get('published', '')}")
            if a.get("summary"):
                lines.append(f"  概要: {a.get('summary', '')}")
            lines.append("")
        return "\n".join(lines)
