import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "1"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
RULES_FILE = Path(os.getenv("RULES_FILE", BASE_DIR / "rules.yaml"))


def load_rules(file_path: str | Path | None = None) -> list[dict]:
    """Read monitoring rules from YAML."""
    path = Path(file_path or RULES_FILE)
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    rules = data.get("rules", [])
    return rules if isinstance(rules, list) else []
