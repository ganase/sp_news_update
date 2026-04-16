"""
メール送信モジュール
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


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
    html = html.replace("{{issue_date}}", issue_date)
    html = html.replace("{{domain_sections}}", domain_sections_html)
    html = html.replace("{{year}}", year)
    html = html.replace("{{from_address}}", from_address)
    return html
