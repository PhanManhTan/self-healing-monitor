import logging
import os
import shutil
import time
from datetime import datetime

from config import BASE_DIR, CHECK_INTERVAL, load_rules
from engine.evaluator import check_and_evaluate


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"


def progress_bar(value: int, width: int = 20) -> str:
    filled = max(0, min(width, int(value / 100 * width)))
    color = RED if value >= 95 else YELLOW if value >= 85 else GREEN
    return f"{color}{'█' * filled}{DIM}{'░' * (width - filled)}{RESET}"


def render(rules: list[dict], results: dict, events: list[dict]) -> None:
    os.system("cls" if os.name == "nt" else "clear")
    width = min(60, shutil.get_terminal_size().columns)

    print(f"{BOLD}{CYAN}Self-Healing Monitor{RESET}  {DIM}{datetime.now():%H:%M:%S}{RESET}")
    print(f"{DIM}{'─' * width}{RESET}")

    metrics = [rule for rule in rules if rule.get("type") in {"cpu", "memory", "disk"}]
    if metrics:
        print(f"\n{BOLD} METRICS{RESET}")
        for rule in metrics:
            result = results.get(rule["name"])
            if not result:
                continue
            value = result.get("value", 0)
            thresholds = "/".join(map(str, rule.get("thresholds", [])))
            state = f" {DIM}[COOLDOWN]{RESET}" if result.get("is_cooldown") else ""
            print(
                f"  {rule['type'].upper():<6} {progress_bar(value)} "
                f"{value:>5.1f}% {DIM}({thresholds}%){RESET}{state}"
            )

    process_rules = [rule for rule in rules if rule.get("type") == "process_auto"]
    if process_rules:
        print(f"\n{BOLD} PROCESSES{RESET}")
        for rule in process_rules:
            result = results.get(rule["name"])
            if not result:
                continue
            ok = "normal" in result["text"].lower()
            marker = f"{GREEN}OK{RESET}" if ok else f"{YELLOW}!!{RESET}"
            print(f"  [{marker}] {result['text']}")

    service_rules = [rule for rule in rules if rule.get("type") == "service"]
    if service_rules:
        print(f"\n{BOLD} SERVICES{RESET}")
        for rule in service_rules:
            result = results.get(rule["name"])
            if not result:
                continue
            status = result["text"].split(": ", 1)[-1]
            icon = f"{GREEN}●{RESET}" if status == "active" else f"{RED}●{RESET}"
            print(f"  {icon} {rule['service_name']:<20} {status}")

    if events:
        print(f"\n{BOLD} RECENT EVENTS{RESET}")
        for event in events[-5:]:
            print(f"  {DIM}{event['time']}{RESET}  {event['message'].splitlines()[0]}")

    print(f"\n{DIM}{'─' * width}{RESET}")
    print(f"{DIM}Ctrl+C to exit | full history: monitor.log{RESET}")


def main() -> None:
    logging.basicConfig(
        filename=BASE_DIR / "monitor.log",
        level=logging.INFO,
        encoding="utf-8",
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    rules = load_rules()
    if not rules:
        print("rules.yaml not found or empty")
        return

    last_check = {rule["name"]: 0.0 for rule in rules}
    results = {}
    events = []

    try:
        while True:
            now = time.time()
            updated = False
            for rule in rules:
                name = rule["name"]
                if now - last_check[name] < int(rule.get("interval", 10)):
                    continue

                try:
                    result = check_and_evaluate(rule)
                    results[name] = result
                    logging.info("%s | %s", name, result["text"])
                    if result.get("alert_msg"):
                        events.append({"time": f"{datetime.now():%H:%M:%S}", "message": result["alert_msg"]})
                        events = events[-10:]
                        logging.warning(result["alert_msg"].replace("\n", " | "))
                except Exception:
                    logging.exception("Rule failed: %s", name)

                last_check[name] = now
                updated = True

            if updated:
                render(rules, results, events)
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logging.info("Monitor stopped")


if __name__ == "__main__":
    main()
