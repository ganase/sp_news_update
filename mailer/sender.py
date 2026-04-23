"""
メール送信モジュール
"""
import base64
import logging
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


OUTLOOK_CLASS_STYLES = {
    "container": "max-width:760px;margin:0 auto;background-color:#ffffff;",
    "header": "background-color:#bf0000;color:#ffffff;padding:28px 36px 24px;text-align:left;border-bottom:5px solid #8f0000;",
    "subtitle": "margin:0;font-size:14px;font-weight:400;color:#ffffff;",
    "contact": "margin:10px 0 0;font-size:12px;font-weight:600;color:#ffffff;",
    "contact-link": "color:#ffffff;text-decoration:underline;font-weight:600;",
    "issue-date": "margin:12px 0 0;font-size:12px;font-weight:600;color:#ffffff;",
    "content": "padding:28px 36px 32px;background-color:#ffffff;",
    "domain-section": "margin:0 0 28px;border:1px solid #e7e7e7;background-color:#ffffff;",
    "summary-intro": "padding:12px 20px 0;font-size:13px;color:#646464;margin:0;",
    "news-item": "padding:18px 20px;border-bottom:1px solid #e7e7e7;background-color:#ffffff;",
    "priority-high": "background-color:#fff7f7;border-left:4px solid #bf0000;",
    "priority-badge": "display:inline-block;padding:3px 8px;background-color:#fbe7e7;color:#8f0000;font-size:11px;font-weight:700;margin-bottom:8px;",
    "category-badge": "display:inline-block;padding:3px 8px;background-color:#edf2f7;color:#2d4f73;font-size:11px;font-weight:700;margin-bottom:8px;",
    "action": "background-color:#f5f8fb;padding:8px 12px;font-size:13px;color:#232323;",
    "business-impact": "background-color:#f5f8fb;padding:8px 12px;font-size:13px;color:#232323;",
    "takeaway": "background-color:#f5f8fb;padding:8px 12px;font-size:13px;color:#232323;",
    "week-summary": "background-color:#f7f7f7;border-top:1px solid #e7e7e7;padding:14px 20px;",
    "other-news": "padding:14px 20px 16px;background-color:#f7f7f7;border-top:1px solid #e7e7e7;",
    "other-news-title": "margin:0 0 8px 0;font-size:13px;font-weight:700;color:#232323;",
    "footer": "background-color:#eeeeee;padding:20px 32px;text-align:center;font-size:11px;color:#666666;border-top:1px solid #d8d8d8;",
    "no-articles": "padding:20px;color:#646464;font-size:13px;text-align:center;",
}

OUTLOOK_TAG_STYLES = {
    "body": "font-family:'Rakuten Sans','Helvetica Neue',Arial,'Hiragino Kaku Gothic ProN','Hiragino Sans',Meiryo,sans-serif;background-color:#f2f3f5;margin:0;padding:0;color:#232323;line-height:1.6;",
    "h1": "margin:0 0 6px 0;font-size:28px;font-weight:700;line-height:1.2;color:#ffffff;",
    "h2": "background-color:#dc143c;margin:0;padding:16px 20px;font-size:18px;font-weight:700;color:#ffffff;",
    "h3": "margin:0 0 8px 0;font-size:16px;font-weight:700;color:#232323;line-height:1.45;",
    "p": "font-size:13px;line-height:1.65;color:#3f3f3f;",
    "a": "color:#9f0000;text-decoration:none;font-weight:600;",
}

OUTLOOK_DOMAIN_HEADING_COLORS = {
    "domain-ai_data": "#2454a6",
    "domain-helpdesk": "#147a5c",
    "domain-security": "#dc143c",
}


class MailSender:
    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str,
                 use_tls: bool, from_address: str, from_name: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.from_address = from_address
        self.from_name = from_name

    def send(self, to_address: str, subject: str, html_body: str) -> bool:
        """
        HTMLメールを送信する

        Args:
            to_address: 宛先メールアドレス
            subject: 件名
            html_body: HTML本文

        Returns:
            送信成功ならTrue
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_address}>"
        msg["To"] = to_address

        # HTMLパートとテキストパート（フォールバック）
        text_body = "このメールはHTML形式です。HTMLに対応したメールクライアントでご覧ください。"
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            if self.use_tls:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_address, [to_address], msg.as_string())
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_address, [to_address], msg.as_string())

            logger.info(f"メール送信成功: {to_address}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP認証エラー: {e}")
        except smtplib.SMTPConnectError as e:
            logger.error(f"SMTP接続エラー ({self.smtp_host}:{self.smtp_port}): {e}")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP送信エラー: {e}")
        except Exception as e:
            logger.error(f"メール送信中に予期しないエラー: {e}")

        return False


def build_email_html(domain_sections_html: str, issue_date: str, year: str, from_address: str) -> str:
    """
    メールHTMLテンプレートにコンテンツを埋め込む

    Args:
        domain_sections_html: 各ドメインセクションのHTML結合文字列
        issue_date: 号の日付文字列
        year: 年
        from_address: 送信元アドレス

    Returns:
        完成したHTML文字列
    """
    template_path = Path(__file__).parent.parent / "templates" / "email.html"
    template = template_path.read_text(encoding="utf-8")

    html = template.replace("{{title}}", f"SP News Update {issue_date}号")
    html = html.replace("{{favicon_href}}", load_favicon_data_uri())
    html = html.replace("{{issue_date}}", issue_date)
    html = html.replace("{{domain_sections}}", domain_sections_html)
    html = html.replace("{{year}}", year)
    html = html.replace("{{from_address}}", from_address)
    return apply_outlook_inline_styles(html)


def apply_outlook_inline_styles(html: str) -> str:
    def replace_opening_tag(match: re.Match) -> str:
        tag = match.group("tag")
        attrs = match.group("attrs")
        tag_lower = tag.lower()
        styles = []

        tag_style = OUTLOOK_TAG_STYLES.get(tag_lower)
        if tag_style:
            styles.append(tag_style)

        class_match = re.search(r'\sclass=(["\'])(.*?)\1', attrs, flags=re.IGNORECASE | re.DOTALL)
        if class_match:
            class_names = class_match.group(2).split()
            for class_name in class_names:
                class_style = OUTLOOK_CLASS_STYLES.get(class_name)
                if class_style:
                    styles.append(class_style)

        if not styles:
            return match.group(0)

        attrs = _append_inline_style(attrs, "".join(styles))
        return f"<{tag}{attrs}>"

    html = re.sub(r"<(?P<tag>[A-Za-z][A-Za-z0-9:-]*)(?P<attrs>[^<>]*)>", replace_opening_tag, html)
    return _apply_domain_heading_styles(html)


def _apply_domain_heading_styles(html: str) -> str:
    for domain_class, color in OUTLOOK_DOMAIN_HEADING_COLORS.items():
        pattern = re.compile(
            rf"(<(?:section|div)\b(?=[^>]*\bdomain-section\b)(?=[^>]*\b{re.escape(domain_class)}\b)[^>]*>\s*<h2\b)(?P<attrs>[^>]*)>",
            flags=re.IGNORECASE,
        )

        def replace_heading(match: re.Match) -> str:
            attrs = _append_inline_style(
                match.group("attrs"),
                f"background-color:{color};margin:0;padding:16px 20px;font-size:18px;font-weight:700;color:#ffffff;",
            )
            return f"{match.group(1)}{attrs}>"

        html = pattern.sub(replace_heading, html)
    return html


def _append_inline_style(attrs: str, style: str) -> str:
    style_match = re.search(r'\sstyle=(["\'])(.*?)\1', attrs, flags=re.IGNORECASE | re.DOTALL)
    if style_match:
        quote = style_match.group(1)
        current_style = style_match.group(2).strip()
        separator = "" if current_style.endswith(";") or not current_style else ";"
        new_style = f"{current_style}{separator}{style}"
        return attrs[:style_match.start()] + f' style={quote}{new_style}{quote}' + attrs[style_match.end():]

    return f'{attrs} style="{style}"'


def load_favicon_data_uri() -> str:
    favicon_path = Path(__file__).parent.parent / "favicon.ico"
    if not favicon_path.exists():
        return "favicon.ico"

    encoded = base64.b64encode(favicon_path.read_bytes()).decode("ascii")
    return f"data:image/x-icon;base64,{encoded}"
