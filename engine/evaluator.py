import shlex
import subprocess
import time
from typing import Any, Callable

from collectors.process import find_heavy_processes
from collectors.service import check_service
from collectors.system import check_cpu, check_disk, check_memory
from notifiers.telegram import send_message


cooldowns: dict[str, float] = {}


def _can_alert(key: str, seconds: int) -> bool:
    now = time.time()
    if now - cooldowns.get(key, 0) < seconds:
        return False
    cooldowns[key] = now
    return True


def _severity(value: int, thresholds: list[int]) -> tuple[int | None, str | None]:
    ordered = sorted(thresholds)
    passed = [threshold for threshold in ordered if value >= threshold]
    if not passed:
        return None, None

    threshold = passed[-1]
    position = ordered.index(threshold)
    if position == len(ordered) - 1:
        return threshold, "DANGER"
    if position == len(ordered) - 2:
        return threshold, "CRITICAL"
    return threshold, "WARNING"


def _metric_result(
    rule: dict[str, Any],
    label: str,
    collector: Callable[[], int],
    defaults: list[int],
) -> dict[str, Any]:
    value = collector()
    result = {"text": f"{label}: {value}%", "value": value, "is_cooldown": False}
    threshold, severity = _severity(value, rule.get("thresholds", defaults))
    if threshold is None:
        return result

    key = f"{rule['name']}:{threshold}"
    if not _can_alert(key, int(rule.get("cooldown", 60))):
        result["is_cooldown"] = True
        return result

    message = (
        f"[{severity}] {label} ALERT\n"
        f"Rule: {rule['name']}\n"
        f"Usage: {value}% (threshold: {threshold}%)"
    )
    send_message(message)
    result["alert_msg"] = message
    return result


def _process_result(rule: dict[str, Any]) -> dict[str, Any]:
    heavy = find_heavy_processes(
        int(rule.get("cpu_threshold", 80)),
        int(rule.get("ram_threshold", 80)),
        rule.get("whitelist"),
    )
    if not heavy:
        return {"text": "All processes normal", "is_cooldown": False}

    result = {"text": f"{len(heavy)} heavy process(es)", "is_cooldown": False}
    if not _can_alert(rule["name"], int(rule.get("cooldown", 30))):
        result["is_cooldown"] = True
        return result

    details = "\n".join(
        f"- {item['name']} (PID {item['pid']}): CPU {item['cpu']}%, RAM {item['ram']}%"
        for item in heavy
    )
    message = f"[WARNING] HEAVY PROCESS\nRule: {rule['name']}\n{details}"
    send_message(message)
    result["alert_msg"] = message
    return result


def _service_result(rule: dict[str, Any]) -> dict[str, Any]:
    service = rule["service_name"]
    status = check_service(service)
    result = {"text": f"Service {service}: {status}", "is_cooldown": False}
    if status != rule.get("if_status", "inactive"):
        return result

    if not _can_alert(rule["name"], int(rule.get("cooldown", 60))):
        result["is_cooldown"] = True
        return result

    command_text = rule.get("action", f"systemctl restart {service}")
    try:
        subprocess.run(
            shlex.split(command_text),
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        message = f"[OK] SERVICE RESTARTED\nService: {service}\nCommand: {command_text}"
    except (OSError, subprocess.SubprocessError) as error:
        message = f"[FAIL] SERVICE RESTART FAILED\nService: {service}\nError: {error}"

    send_message(message)
    result["alert_msg"] = message
    return result


def check_and_evaluate(rule: dict[str, Any]) -> dict[str, Any]:
    """Collect and evaluate one monitoring rule."""
    rule_type = rule.get("type")

    if rule_type == "cpu":
        return _metric_result(rule, "CPU", check_cpu, [70, 85, 95])
    if rule_type == "memory":
        return _metric_result(rule, "RAM", check_memory, [70, 85, 95])
    if rule_type == "disk":
        path = rule.get("mount_path", "/")
        return _metric_result(rule, "DISK", lambda: check_disk(path), [80, 90, 95])
    if rule_type == "process_auto":
        return _process_result(rule)
    if rule_type == "service":
        return _service_result(rule)

    return {"text": f"Unknown rule type: {rule_type}", "is_cooldown": False}
