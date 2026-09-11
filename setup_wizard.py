import sys
import yaml
import subprocess

RULES_FILE = "rules.yaml"


def _send_setup_summary(rules):
    """Send setup summary to Telegram to verify notification is working."""
    try:
        from notifiers.telegram import send_message
        from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("\n   Telegram not configured. Skipping test notification.")
            print("   Edit .env to add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
            return

        lines = ["*Self-Healing Monitor — Setup Complete*\n"]

        for r in rules:
            rtype = r.get("type", "")
            if rtype in ("cpu", "memory", "disk"):
                thresholds = r.get("thresholds", [])
                thresh_str = "/".join(str(t) + "%" for t in thresholds)
                lines.append(f"  {r['name']} — notify at {thresh_str}")
            elif rtype == "process_auto":
                lines.append(f"  {r['name']} — CPU>{r.get('cpu_threshold')}% RAM>{r.get('ram_threshold')}%")
            elif rtype == "service":
                lines.append(f"  {r['name']} — auto-restart if inactive")

        lines.append(f"\nTotal: {len(rules)} rule(s)")
        lines.append("Notification test: OK")

        msg = "\n".join(lines)
        ok = send_message(msg)
        if ok:
            print("\n   Telegram test sent. Check your chat.")
        else:
            print("\n   Telegram test failed.")
            print("   If 403: open your bot in Telegram and send /start first.")
            print("   If 401: check TELEGRAM_BOT_TOKEN in .env.")
    except Exception as e:
        print(f"\n   Telegram test failed: {e}")


def save_rules(data):
    with open(RULES_FILE, "w", encoding="utf8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


def scan_active_services():
    """Scan currently running systemd services, filter out system internals."""
    skip_prefixes = (
        "systemd-", "dbus", "getty", "user@", "user-", "init-",
        "console-", "plymouth", "polkit", "udisks", "accounts-daemon",
        "ModemManager", "wpa_supplicant", "avahi", "colord", "upower",
        "NetworkManager-", "switcheroo", "thermald", "power-profiles",
    )
    try:
        result = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--state=running",
             "--no-pager", "--plain", "--no-legend"],
            capture_output=True, text=True, timeout=10
        )
        services = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if parts:
                name = parts[0].replace(".service", "")
                if not any(name.startswith(p) for p in skip_prefixes):
                    services.append(name)
        return sorted(services)
    except Exception:
        return []


def validate_services(names):
    """Validate service names against systemctl. Returns (valid, invalid)."""
    valid, invalid = [], []
    for name in names:
        try:
            result = subprocess.run(
                ["systemctl", "list-unit-files", f"{name}.service",
                 "--no-pager", "--plain", "--no-legend"],
                capture_output=True, text=True, timeout=5
            )
            if name in result.stdout:
                valid.append(name)
            else:
                invalid.append(name)
        except Exception:
            valid.append(name)
    return valid, invalid


def build_default_rules():
    """Build the default monitoring rules."""
    return [
        {"name": "Monitor CPU", "type": "cpu",
         "thresholds": [70, 85, 95], "cooldown": 60, "interval": 10},
        {"name": "Monitor RAM", "type": "memory",
         "thresholds": [70, 85, 95], "cooldown": 60, "interval": 10},
        {"name": "Monitor Disk", "type": "disk",
         "mount_path": "/", "thresholds": [80, 90, 95], "cooldown": 300, "interval": 60},
        {"name": "Monitor Processes", "type": "process_auto",
         "cpu_threshold": 80, "ram_threshold": 80, "cooldown": 30, "interval": 10},
    ]


def build_service_rules(svc_names):
    """Build service rules from a list of service names."""
    return [
        {"name": f"Monitor {name}", "type": "service",
         "service_name": name, "if_status": "inactive",
         "action": f"systemctl restart {name}",
         "cooldown": 60, "interval": 10}
        for name in svc_names
    ]


def parse_thresholds(user_input, defaults):
    """Parse comma-separated thresholds like '70,85,95' or return defaults."""
    if not user_input:
        return defaults
    try:
        return sorted([int(x.strip()) for x in user_input.split(",") if x.strip().isdigit()])
    except ValueError:
        return defaults


# ═══════════════════════════════════════════════════════
# Default mode: auto-configure everything, no questions
# ═══════════════════════════════════════════════════════

def run_default():
    print("=== Self-Healing Monitor — Quick Setup ===\n")

    rules = build_default_rules()

    print("  [CPU]     notify at 70%, 85%, 95%")
    print("  [RAM]     notify at 70%, 85%, 95%")
    print("  [Disk]    notify at 80%, 90%, 95%")
    print("  [Process] notify heavy CPU>80% RAM>80%")

    # Auto-detect and add services
    detected = scan_active_services()
    if detected:
        svc_names = detected[:5]
        rules.extend(build_service_rules(svc_names))
        print(f"  [Service] auto-restart: {', '.join(svc_names)}")
    else:
        print("  [Service] no running services detected (edit rules.yaml to add)")

    save_rules({"rules": rules})
    print(f"\n-> Saved {len(rules)} rule(s) to rules.yaml")
    print("   Run with --custom to customize.")

    # Send test notification to Telegram
    _send_setup_summary(rules)


# ═══════════════════════════════════════════════════════
# Custom mode: interactive, let user override everything
# ═══════════════════════════════════════════════════════

def run_custom():
    print("=== Self-Healing Monitor — Custom Setup ===")
    print("Press Enter for defaults. Type 'skip' to disable a module.\n")

    rules = []

    # [CPU]
    v = input("[CPU]     thresholds%(70,85,95): ").strip()
    if v.lower() != "skip":
        rules.append({
            "name": "Monitor CPU", "type": "cpu",
            "thresholds": parse_thresholds(v, [70, 85, 95]),
            "cooldown": 60, "interval": 10
        })

    # [RAM]
    v = input("[RAM]     thresholds%(70,85,95): ").strip()
    if v.lower() != "skip":
        rules.append({
            "name": "Monitor RAM", "type": "memory",
            "thresholds": parse_thresholds(v, [70, 85, 95]),
            "cooldown": 60, "interval": 10
        })

    # [Disk]
    v = input("[Disk]    thresholds%(80,90,95): ").strip()
    if v.lower() != "skip":
        rules.append({
            "name": "Monitor Disk", "type": "disk",
            "mount_path": "/", "thresholds": parse_thresholds(v, [80, 90, 95]),
            "cooldown": 300, "interval": 60
        })

    # [Process]
    v = input("[Process] CPU>(80)% RAM>(80)%: ").strip()
    if v.lower() != "skip":
        cpu_t, ram_t = 80, 80
        if v:
            parts = v.split()
            if len(parts) >= 1 and parts[0].isdigit():
                cpu_t = int(parts[0])
            if len(parts) >= 2 and parts[1].isdigit():
                ram_t = int(parts[1])
        rules.append({
            "name": "Monitor Processes", "type": "process_auto",
            "cpu_threshold": cpu_t, "ram_threshold": ram_t,
            "cooldown": 30, "interval": 10
        })

    # [Service]
    detected = scan_active_services()
    default_svcs = ",".join(detected[:5]) if detected else "nginx,mysql,docker"
    if detected:
        print(f"  Detected running: {', '.join(detected[:15])}")

    v = input(f"[Service] auto-restart, comma-separated ({default_svcs}): ").strip()
    if v.lower() != "skip":
        svc_names = [s.strip() for s in (v or default_svcs).split(",") if s.strip()]
        valid, invalid = validate_services(svc_names)
        if invalid:
            print(f"  Warning: not found: {', '.join(invalid)} (skipped)")
        rules.extend(build_service_rules(valid))

    # Confirm
    if not rules:
        print("\nNo rules configured.")
        return

    v = input(f"\n-> Created {len(rules)} rule(s). Save to rules.yaml? (y): ").strip()
    if v.lower() in ("", "y", "yes"):
        save_rules({"rules": rules})
        print("Done. Saved to rules.yaml")
        _send_setup_summary(rules)
    else:
        print("Cancelled.")


# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    if "--custom" in sys.argv:
        run_custom()
    else:
        run_default()
