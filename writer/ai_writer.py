"""
AI記事生成モジュール

対応プロバイダー:
  - rakuten : Rakuten AI (OpenAI互換)
  - gemini  : Google Gemini (OpenAI互換エンドポイント経由)
  - openai  : OpenAI GPT-4o / GPT-4o mini
  - claude  : Anthropic Claude

config.yaml の ai.provider で切り替えます。
"""
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)


def create_writer_from_config(ai_cfg: dict) -> "AIWriter":
    """
    config.yaml の ai セクションから適切な AIWriter を生成するファクトリ関数
    """
    provider = ai_cfg.get("provider", "rakuten").lower()
    max_tokens = ai_cfg.get("max_tokens", 4096)
    temperature = ai_cfg.get("temperature", 0.3)

    if provider == "rakuten":
        cfg = ai_cfg["rakuten"]
        return AIWriter(
            provider="rakuten",
            endpoint=cfg["endpoint"],
            api_key=cfg["api_key"],
            model=cfg["model"],
            max_tokens=max_tokens,
            temperature=temperature,
        )
    elif provider == "gemini":
        cfg = ai_cfg["gemini"]
        # Gemini の OpenAI互換エンドポイント
        # 完全なURLは https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
        return AIWriter(
            provider="gemini",
            endpoint="https://generativelanguage.googleapis.com/v1beta/openai",
            api_key=cfg["api_key"],
            model=cfg["model"],
            max_tokens=max_tokens,
            temperature=temperature,
            chat_path="/chat/completions",
        )
    elif provider == "openai":
        cfg = ai_cfg["openai"]
        return AIWriter(
            provider="openai",
            endpoint="https://api.openai.com",
            api_key=cfg["api_key"],
            model=cfg["model"],
            max_tokens=max_tokens,
            temperature=temperature,
        )
    elif provider == "claude":
        cfg = ai_cfg["claude"]
        return ClaudeWriter(
            api_key=cfg["api_key"],
            model=cfg["model"],
            max_tokens=max_tokens,
        )
    else:
        raise ValueError(f"未対応のプロバイダー: {provider}。rakuten / gemini / openai / claude を指定してください。")


class AIWriter:
    """
    OpenAI互換API用ライター（Rakuten AI・Gemini・OpenAI 共通）
    """
    def __init__(self, provider: str, endpoint: str, api_key: str, model: str,
                 max_tokens: int = 4096, temperature: float = 0.3, chat_path: str = "/v1/chat/completions"):
        self.provider = provider
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.chat_path = chat_path

    def generate_domain_section(
        self,
        system_prompt: str,
        article_prompt_template: str,
        articles: list[dict],
    ) -> Optional[str]:
        if not articles:
            logger.warning("記事が0件のため生成をスキップします")
            return None

        articles_text = _format_articles(articles)
        user_prompt = article_prompt_template.replace("{articles}", articles_text)

        try:
            response = requests.post(
                f"{self.endpoint}{self.chat_path}",
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
            logger.info(f"[{self.provider}] AI生成完了 (tokens: {data.get('usage', {}).get('total_tokens', '?')})")
            return content

        except requests.RequestException as e:
            logger.error(f"[{self.provider}] API呼び出しエラー: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"レスポンス: {e.response.text[:500]}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"[{self.provider}] レスポンス解析エラー: {e}")
            return None


class ClaudeWriter:
    """
    Anthropic Claude 専用ライター（独自API形式）
    """
    def __init__(self, api_key: str, model: str, max_tokens: int = 4096):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    def generate_domain_section(
        self,
        system_prompt: str,
        article_prompt_template: str,
        articles: list[dict],
    ) -> Optional[str]:
        if not articles:
            logger.warning("記事が0件のため生成をスキップします")
            return None

        articles_text = _format_articles(articles)
        user_prompt = article_prompt_template.replace("{articles}", articles_text)

        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            content = data["content"][0]["text"].strip()
            logger.info(f"[claude] AI生成完了 (tokens: {data.get('usage', {}).get('output_tokens', '?')})")
            return content

        except requests.RequestException as e:
            logger.error(f"[claude] API呼び出しエラー: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"レスポンス: {e.response.text[:500]}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"[claude] レスポンス解析エラー: {e}")
            return None


def _format_articles(articles: list[dict]) -> str:
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
