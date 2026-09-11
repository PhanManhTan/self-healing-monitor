import os
import time
import shutil
from datetime import datetime
from config import load_rules
from engine.evaluator import check_and_evaluate


# ── ANSI Colors ──
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
BG_RED = "\033[41m"


def progress_bar(value, width=20):
    """Render a simple ASCII progress bar with color."""
    filled = int(value / 100 * width)
    empty = width - filled
    if value >= 95:
        color = RED
    elif value >= 85:
        color = YELLOW
    else:
        color = GREEN
    return f"{color}{'█' * filled}{DIM}{'░' * empty}{RESET}"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def main():
    rules = load_rules()
    if not rules:
        print("[!] rules.yaml not found or empty.")
        return

    last_check_time = {rule["name"]: 0 for rule in rules}
    latest_results = {}
    event_log = []  # Store recent events

    clear_screen()
    print(f"{BOLD}{CYAN}Self-Healing Monitor — Running{RESET}")
    print(f"{DIM}Press Ctrl+C to exit{RESET}\n")

    while True:
        now = time.time()
        updated = False

        for rule in rules:
            rule_name = rule["name"]
            interval = rule.get("interval", 10)

            if now - last_check_time[rule_name] >= interval:
                result = check_and_evaluate(rule)
                latest_results[rule_name] = result
                last_check_time[rule_name] = now
                updated = True

                # Capture events
                if result.get("alert_msg"):
                    event_log.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "rule": rule_name,
                        "msg": result["alert_msg"]
                    })
                    if len(event_log) > 10:
                        event_log.pop(0)

        if not updated:
            time.sleep(1)
            continue

        # ── Render Dashboard ──
        term_width = shutil.get_terminal_size().columns
        clear_screen()

        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{BOLD}{CYAN}Self-Healing Monitor{RESET}  {DIM}{timestamp}{RESET}")
        print(f"{DIM}{'─' * min(60, term_width)}{RESET}")

        # Group rules by type
        metrics = []   # cpu, memory, disk
        processes = [] # process_auto
        services = []  # service

        for rule in rules:
            name = rule["name"]
            r = latest_results.get(name)
            if not r:
                continue
            rtype = rule.get("type")
            if rtype in ("cpu", "memory", "disk"):
                metrics.append((name, rule, r))
            elif rtype == "process_auto":
                processes.append((name, rule, r))
            elif rtype == "service":
                services.append((name, rule, r))

        # ── Metrics Section ──
        if metrics:
            print(f"\n{BOLD} METRICS{RESET}")
            for name, rule, r in metrics:
                value = r.get("value", 0)
                bar = progress_bar(value)
                status = ""
                if r.get("is_cooldown"):
                    status = f" {DIM}[COOLDOWN]{RESET}"
                elif r.get("is_alert"):
                    status = f" {RED}[ALERT]{RESET}"

                label = rule.get("type", "").upper()
                thresholds = rule.get("thresholds", [])
                thresh_str = f"{DIM}({'/'.join(str(t) for t in thresholds)}%){RESET}" if thresholds else ""

                print(f"  {label:<6} {bar} {value:>5.1f}% {thresh_str}{status}")

        # ── Process Section ──
        if processes:
            print(f"\n{BOLD} PROCESSES{RESET}")
            for name, rule, r in processes:
                text = r.get("text", "")
                status = ""
                if r.get("is_cooldown"):
                    status = f" {DIM}[COOLDOWN]{RESET}"
                elif r.get("is_alert"):
                    status = f" {RED}[ALERT]{RESET}"
                marker = f"{GREEN}OK{RESET}" if "normal" in text.lower() else f"{YELLOW}!!{RESET}"
                print(f"  [{marker}] {text}{status}")

        # ── Service Section ──
        if services:
            print(f"\n{BOLD} SERVICES{RESET}")
            for name, rule, r in services:
                svc_name = rule.get("service_name", "?")
                text = r.get("text", "")
                if "active" in text.lower() and "inactive" not in text.lower():
                    icon = f"{GREEN}●{RESET}"
                    label = "active"
                else:
                    icon = f"{RED}●{RESET}"
                    label = text.replace("Status: ", "")
                status = ""
                if r.get("is_cooldown"):
                    status = f" {DIM}[COOLDOWN]{RESET}"
                elif r.get("is_alert"):
                    status = f" {YELLOW}[RESTARTING]{RESET}"
                print(f"  {icon} {svc_name:<20} {label}{status}")

        # ── Event Log ──
        if event_log:
            print(f"\n{BOLD} RECENT EVENTS{RESET}")
            for evt in event_log[-5:]:
                # Show first line of alert message
                first_line = evt["msg"].split("\n")[0]
                print(f"  {DIM}{evt['time']}{RESET}  {first_line}")

        print(f"\n{DIM}{'─' * min(60, term_width)}{RESET}")
        print(f"{DIM}Ctrl+C to exit | rules.yaml to configure{RESET}")

        time.sleep(1)


if __name__ == "__main__":
    main()
