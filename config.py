import os
import yaml
from dotenv import load_dotenv

load_dotenv()

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 10))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def load_rules(file_path: str = "rules.yaml") -> list:
    """Load monitoring rules from YAML configuration."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf8") as f:
        data = yaml.safe_load(f)
        return data.get("rules", [])
