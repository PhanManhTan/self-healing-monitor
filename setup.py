import subprocess
import sys

import yaml

from config import BASE_DIR
from notifiers.telegram import send_message


DEFAULT_RULES = [
    {"name": "Monitor CPU", "type": "cpu", "thresholds": [70, 85, 95], "cooldown": 60, "interval": 10},
    {"name": "Monitor RAM", "type": "memory", "thresholds": [70, 85, 95], "cooldown": 60, "interval": 10},
    {"name": "Monitor Disk", "type": "disk", "mount_path": "/", "thresholds": [80, 90, 95], "cooldown": 300, "interval": 60},
    {"name": "Monitor Processes", "type": "process_auto", "cpu_threshold": 80, "ram_threshold": 80, "cooldown": 30, "interval": 10},
]


def find_services() -> list[str]:
    """Find up to five running systemd services."""
    try:
        result = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--state=running", "--no-legend"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    services = []
    for line in result.stdout.splitlines():
        if line.split():
            services.append(line.split()[0].removesuffix(".service"))
    return services[:5]


def service_rule(name: str) -> dict:
    return {
        "name": f"Monitor {name}",
        "type": "service",
        "service_name": name,
        "if_status": "inactive",
        "action": f"systemctl restart {name}",
        "cooldown": 60,
        "interval": 10,
    }


def main() -> None:
    services = find_services()
    if "--custom" in sys.argv:
        value = input("Services (comma-separated, blank = none): ").strip()
        services = [name.strip() for name in value.split(",") if name.strip()]

    rules = DEFAULT_RULES + [service_rule(name) for name in services]
    with (BASE_DIR / "rules.yaml").open("w", encoding="utf-8") as file:
        yaml.safe_dump({"rules": rules}, file, sort_keys=False)

    print(f"Saved {len(rules)} rules to rules.yaml")
    send_message(f"Monitor setup complete: {len(rules)} rules")


if __name__ == "__main__":
    main()
