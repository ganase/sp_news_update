"""
Browser admin console for SP News Update.

Run:
  python admin.py
Then open:
  http://127.0.0.1:8000/
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

import yaml


BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"
PROMPTS_DIR = BASE_DIR / "prompts"
LOGS_DIR = BASE_DIR / "logs"
FAVICON_PATH = BASE_DIR / "favicon.ico"
HOST = "127.0.0.1"
PORT = 8000


DOMAIN_COLORS = {
    "security": "#dc143c",
    "ai_data": "#2454a6",
    "helpdesk": "#147a5c",
}


class AdminHandler(BaseHTTPRequestHandler):
    server_version = "SPNewsAdmin/1.0"

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self.redirect("/prompts")
        if path == "/favicon.ico":
            return self.serve_favicon()
        if path == "/prompts":
            return self.render_prompts()
        if path == "/history":
            return self.render_history()
        if path.startswith("/preview/"):
            return self.serve_preview(unquote(path.removeprefix("/preview/")))
        return self.not_found()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/prompts/save":
            return self.save_prompt()
        return self.not_found()

    def render_prompts(self, message: str = ""):
        config = load_config()
        cards = []
        for domain in config.get("domains", []):
            prompt_file = domain.get("prompt_file", "")
            prompt_path = safe_prompt_path(prompt_file)
            prompt = load_prompt(prompt_path)
            domain_id = domain.get("id", "")
            color = DOMAIN_COLORS.get(domain_id, "#bf0000")
            cards.append(
                f"""
                <section class="panel prompt-panel" style="--accent:{esc(color)}">
                  <form method="post" action="/prompts/save">
                    <input type="hidden" name="prompt_file" value="{esc(prompt_file)}">
                    <div class="panel-head">
                      <div>
                        <p class="eyebrow">{esc(prompt_file)}</p>
                        <h2>{esc(domain.get("name", domain_id))}</h2>
                      </div>
                      <button type="submit">保存</button>
                    </div>
                    <label>システムプロンプト</label>
                    <textarea name="system_prompt" spellcheck="false">{esc(prompt.get("system_prompt", ""))}</textarea>
                    <label>記事作成プロンプト</label>
                    <textarea name="article_prompt" spellcheck="false">{esc(prompt.get("article_prompt", ""))}</textarea>
                  </form>
                </section>
                """
            )

        body = f"""
        <div class="page-title">
          <h1>プロンプト管理</h1>
          <p>本文だけを編集できます。保存時にYAMLは自動整形されるため、インデントを意識する必要はありません。</p>
        </div>
        {notice(message)}
        <div class="stack">{"".join(cards)}</div>
        """
        return self.html_response(layout("prompts", body))

    def save_prompt(self):
        length = int(self.headers.get("Content-Length", "0"))
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        prompt_file = first(form, "prompt_file")
        prompt_path = safe_prompt_path(prompt_file)
        prompt = load_prompt(prompt_path)
        prompt["system_prompt"] = first(form, "system_prompt")
        prompt["article_prompt"] = first(form, "article_prompt")

        backup_path = prompt_path.with_suffix(prompt_path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        backup_path.write_text(prompt_path.read_text(encoding="utf-8"), encoding="utf-8")
        prompt_path.write_text(
            yaml.safe_dump(prompt, allow_unicode=True, sort_keys=False, width=1000),
            encoding="utf-8",
        )
        return self.render_prompts(f"{prompt_file} を保存しました。バックアップ: {backup_path.name}")

    def render_history(self):
        previews = list_previews()
        logs = list_logs()
        preview_rows = []
        for preview in previews:
            preview_rows.append(
                f"""
                <tr>
                  <td>{esc(preview.name)}</td>
                  <td>{esc(format_mtime(preview))}</td>
                  <td>{preview.stat().st_size:,} bytes</td>
                  <td><a class="link-button" href="/preview/{quote(preview.name)}" target="_blank">開く</a></td>
                </tr>
                """
            )

        article_blocks = []
        for log_path in logs[:6]:
            entries = parse_log_articles(log_path)
            if not entries:
                continue
            rows = []
            for entry in entries:
                rows.append(
                    f"""
                    <tr>
                      <td><span class="tag">{esc(entry["domain"])}</span></td>
                      <td>{esc(entry["source"])}</td>
                      <td>{esc(entry["title"])}</td>
                    </tr>
                    """
                )
            article_blocks.append(
                f"""
                <section class="panel">
                  <div class="panel-head">
                    <div>
                      <p class="eyebrow">収集記事ログ</p>
                      <h2>{esc(log_path.name)}</h2>
                    </div>
                    <span class="meta">{esc(format_mtime(log_path))}</span>
                  </div>
                  <div class="table-wrap">
                    <table>
                      <thead><tr><th>カテゴリ</th><th>情報源</th><th>タイトル</th></tr></thead>
                      <tbody>{"".join(rows)}</tbody>
                    </table>
                  </div>
                </section>
                """
            )

        body = f"""
        <div class="page-title">
          <h1>記事履歴</h1>
          <p>過去のプレビューHTMLと、実行ログに記録された収集記事を確認できます。</p>
        </div>
        <section class="panel">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Preview</p>
              <h2>生成済みプレビュー</h2>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>ファイル</th><th>更新日時</th><th>サイズ</th><th></th></tr></thead>
              <tbody>{"".join(preview_rows) or '<tr><td colspan="4">プレビューはまだありません。</td></tr>'}</tbody>
            </table>
          </div>
        </section>
        <div class="stack">{"".join(article_blocks) or '<section class="panel">収集記事ログはまだありません。</section>'}</div>
        """
        return self.html_response(layout("history", body))

    def serve_preview(self, filename: str):
        if "/" in filename or "\\" in filename:
            return self.not_found()
        path = LOGS_DIR / filename
        if not path.exists() or path.suffix.lower() != ".html":
            return self.not_found()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def serve_favicon(self):
        if not FAVICON_PATH.exists():
            return self.not_found()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/x-icon")
        self.end_headers()
        self.wfile.write(FAVICON_PATH.read_bytes())

    def redirect(self, location: str):
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def html_response(self, content: str):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def not_found(self):
        self.send_error(HTTPStatus.NOT_FOUND)


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def load_prompt(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def safe_prompt_path(prompt_file: str) -> Path:
    path = (PROMPTS_DIR / prompt_file).resolve()
    if PROMPTS_DIR.resolve() not in path.parents or path.suffix.lower() != ".yaml":
        raise ValueError("Invalid prompt file")
    return path


def list_previews() -> list[Path]:
    if not LOGS_DIR.exists():
        return []
    return sorted(LOGS_DIR.glob("preview_*.html"), key=lambda p: p.stat().st_mtime, reverse=True)


def list_logs() -> list[Path]:
    if not LOGS_DIR.exists():
        return []
    return sorted(LOGS_DIR.glob("run_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)


def parse_log_articles(path: Path) -> list[dict]:
    entries = []
    pattern = re.compile(r"\[(?P<domain>[^\]]+)\]\s+収集記事\s+\d+:\s+(?P<source>.*?)\s+\|\s+(?P<title>.*)$")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.search(line)
        if match:
            entries.append(match.groupdict())
    return entries


def layout(active: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SP News Update Admin</title>
  <link rel="icon" href="/favicon.ico" type="image/x-icon">
  <style>{admin_css()}</style>
</head>
<body>
  <header>
    <div>
      <h1>SP News Update Admin</h1>
      <p>Rakuten-branded editorial control</p>
    </div>
    <nav>
      <a class="{active_class(active, "prompts")}" href="/prompts">プロンプト</a>
      <a class="{active_class(active, "history")}" href="/history">記事履歴</a>
    </nav>
  </header>
  <main>{body}</main>
</body>
</html>"""


def admin_css() -> str:
    return """
    :root {
      --red: #bf0000;
      --ink: #232323;
      --muted: #666;
      --line: #e6e6e6;
      --soft: #f6f7f8;
      --white: #fff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: 'Rakuten Sans', 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', 'Hiragino Sans', Meiryo, sans-serif;
      color: var(--ink);
      background: #f2f3f5;
      line-height: 1.6;
    }
    header {
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: center;
      padding: 22px 32px;
      color: var(--white);
      background: var(--red);
      border-bottom: 5px solid #8f0000;
    }
    header h1 {
      margin: 0;
      font-size: 24px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    header p {
      margin: 4px 0 0;
      font-size: 13px;
      opacity: .9;
    }
    nav {
      display: flex;
      gap: 10px;
    }
    nav a, button, .link-button {
      border: 1px solid transparent;
      border-radius: 4px;
      padding: 8px 12px;
      font: inherit;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
    }
    nav a {
      color: #fff;
      background: rgba(255,255,255,.12);
    }
    nav a.active {
      color: var(--red);
      background: #fff;
    }
    button, .link-button {
      color: #fff;
      background: var(--red);
    }
    main {
      width: min(1120px, calc(100% - 32px));
      margin: 28px auto 48px;
    }
    .page-title {
      margin-bottom: 22px;
    }
    .page-title h1 {
      margin: 0 0 6px;
      font-size: 26px;
      letter-spacing: 0;
    }
    .page-title p, .meta {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }
    .stack {
      display: grid;
      gap: 18px;
    }
    .panel {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      margin-bottom: 18px;
    }
    .prompt-panel {
      border-top: 6px solid var(--accent, var(--red));
    }
    .panel-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      padding: 18px 20px;
      background: var(--soft);
      border-bottom: 1px solid var(--line);
    }
    .panel h2 {
      margin: 0;
      font-size: 18px;
    }
    .eyebrow {
      margin: 0 0 2px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    form label {
      display: block;
      margin: 16px 20px 6px;
      font-weight: 700;
      font-size: 13px;
    }
    textarea {
      display: block;
      width: calc(100% - 40px);
      min-height: 220px;
      margin: 0 20px 18px;
      padding: 12px;
      border: 1px solid #d4d4d4;
      border-radius: 4px;
      color: var(--ink);
      font: 14px/1.6 Consolas, 'Yu Gothic UI', monospace;
      resize: vertical;
    }
    .notice {
      margin: 0 0 18px;
      padding: 12px 14px;
      border-left: 4px solid #147a5c;
      background: #eef8f4;
      color: #174d3c;
      font-weight: 700;
    }
    .table-wrap {
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }
    th {
      background: #fafafa;
      font-weight: 700;
    }
    .tag {
      display: inline-block;
      border-radius: 4px;
      padding: 2px 6px;
      background: #f0f0f0;
      font-weight: 700;
      white-space: nowrap;
    }
    @media (max-width: 720px) {
      header {
        display: block;
        padding: 20px;
      }
      nav {
        margin-top: 16px;
      }
      .panel-head {
        display: block;
      }
      .panel-head button {
        margin-top: 12px;
      }
    }
    """


def active_class(active: str, name: str) -> str:
    return "active" if active == name else ""


def notice(message: str) -> str:
    return f'<div class="notice">{esc(message)}</div>' if message else ""


def first(form: dict[str, list[str]], key: str) -> str:
    return form.get(key, [""])[0]


def format_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def main():
    LOGS_DIR.mkdir(exist_ok=True)
    print(json.dumps({"url": f"http://{HOST}:{PORT}/"}, ensure_ascii=False))
    ThreadingHTTPServer((HOST, PORT), AdminHandler).serve_forever()


if __name__ == "__main__":
    main()
