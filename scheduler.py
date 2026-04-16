"""
スケジューラー - 毎週月曜日8時に main.py を実行する

使い方:
  python scheduler.py        # スケジューラー起動（常駐）
  python scheduler.py --now  # 即時実行（テスト用）
"""
import argparse
import logging
import sys
from pathlib import Path

import schedule
import time

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def load_schedule_config() -> dict:
    import yaml
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("schedule", {"day_of_week": "monday", "hour": 8, "minute": 0})


def run_job(dry_run: bool = False):
    """メインジョブを実行する"""
    import subprocess
    logger.info("ジョブ開始")
    cmd = [sys.executable, str(Path(__file__).parent / "main.py")]
    if dry_run:
        cmd.append("--dry-run")
    result = subprocess.run(cmd, cwd=str(Path(__file__).parent))
    if result.returncode != 0:
        logger.error(f"ジョブ失敗 (returncode={result.returncode})")
    else:
        logger.info("ジョブ完了")


def setup_schedule(sched_cfg: dict, dry_run: bool = False):
    """config.yaml の schedule 設定に基づいてスケジュールを登録する"""
    day = sched_cfg.get("day_of_week", "monday").lower()
    hour = sched_cfg.get("hour", 8)
    minute = sched_cfg.get("minute", 0)
    time_str = f"{hour:02d}:{minute:02d}"

    day_map = {
        "monday": schedule.every().monday,
        "tuesday": schedule.every().tuesday,
        "wednesday": schedule.every().wednesday,
        "thursday": schedule.every().thursday,
        "friday": schedule.every().friday,
        "saturday": schedule.every().saturday,
        "sunday": schedule.every().sunday,
    }

    if day not in day_map:
        logger.error(f"無効な曜日設定: {day}. monday〜sunday で設定してください。")
        sys.exit(1)

    day_map[day].at(time_str).do(run_job, dry_run=dry_run)
    logger.info(f"スケジュール設定: 毎週{day} {time_str} に実行")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SP News Update スケジューラー")
    parser.add_argument("--now", action="store_true", help="即時実行（テスト用）")
    parser.add_argument("--dry-run", action="store_true", help="メール送信なし（テスト用）")
    args = parser.parse_args()

    if args.now:
        logger.info("即時実行モード")
        run_job(dry_run=args.dry_run)
        sys.exit(0)

    sched_cfg = load_schedule_config()
    setup_schedule(sched_cfg, dry_run=args.dry_run)

    logger.info("スケジューラー起動。Ctrl+C で停止。")
    while True:
        schedule.run_pending()
        time.sleep(30)
