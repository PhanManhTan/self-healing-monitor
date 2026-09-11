import time
import subprocess
from typing import Dict, Any
from notifiers.telegram import send_message
from collectors.service import check_service
from collectors.system import check_disk

cooldown_memory: Dict[str, float] = {}


def _get_severity(value, thresholds):
    """Determine alert severity based on which threshold is exceeded."""
    thresholds = sorted(thresholds)
    exceeded = [t for t in thresholds if value >= t]
    if not exceeded:
        return None, None
    highest = exceeded[-1]
    idx = thresholds.index(highest)
    if idx == len(thresholds) - 1:
        return highest, "[DANGER]"
    elif idx == len(thresholds) - 2:
        return highest, "[CRITICAL]"
    else:
        return highest, "[WARNING]"


def _handle_threshold_alert(rule_name, metric_name, value, threshold, severity, cooldown):
    """Send notification for threshold-based alerts. Returns (alert_msg, is_cooldown)."""
    cooldown_key = f"{rule_name}_{threshold}"
    last_run = cooldown_memory.get(cooldown_key, 0)
    now = time.time()

    if now - last_run < cooldown:
        return None, True

    alert_msg = (
        f"{severity} *{metric_name} ALERT*\n"
        f"Rule: {rule_name}\n"
        f"Usage: {value}% (threshold: {threshold}%)"
    )
    cooldown_memory[cooldown_key] = now
    send_message(alert_msg)
    return alert_msg, False


def check_and_evaluate(rule: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate a single rule and trigger actions if necessary.
    Returns a structured dictionary with state and alert info.
    """
    rule_name = rule["name"]
    rtype = rule.get("type")
    
    result = {
        "text": "Unknown",
        "value": None,
        "type": "text",
        "is_alert": False,
        "alert_msg": None,
        "is_cooldown": False
    }
    
    # ═══════════════════════════════════════════════
    # THRESHOLD-BASED MONITORS (notify only)
    # CPU / RAM / Disk — same pattern
    # ═══════════════════════════════════════════════

    if rtype == "cpu":
        from collectors.system import check_cpu
        usage = check_cpu()
        result["type"] = "percent"
        result["value"] = usage
        result["text"] = f"CPU: {usage}%"

        thresholds = rule.get("thresholds", [70, 85, 95])
        threshold, severity = _get_severity(usage, thresholds)
        if threshold is not None:
            alert_msg, is_cd = _handle_threshold_alert(
                rule_name, "CPU USAGE", usage, threshold, severity,
                rule.get("cooldown", 60)
            )
            result["is_alert"] = not is_cd
            result["is_cooldown"] = is_cd
            result["alert_msg"] = alert_msg

    elif rtype == "memory":
        from collectors.system import check_memory
        usage = check_memory()
        result["type"] = "percent"
        result["value"] = usage
        result["text"] = f"RAM: {usage}%"

        thresholds = rule.get("thresholds", [70, 85, 95])
        threshold, severity = _get_severity(usage, thresholds)
        if threshold is not None:
            alert_msg, is_cd = _handle_threshold_alert(
                rule_name, "MEMORY USAGE", usage, threshold, severity,
                rule.get("cooldown", 60)
            )
            result["is_alert"] = not is_cd
            result["is_cooldown"] = is_cd
            result["alert_msg"] = alert_msg

    elif rtype == "disk":
        usage = check_disk(rule.get("mount_path", "/"))
        result["type"] = "percent"
        result["value"] = usage
        result["text"] = f"Disk: {usage}%"

        thresholds = rule.get("thresholds", [80, 90, 95])
        threshold, severity = _get_severity(usage, thresholds)
        if threshold is not None:
            alert_msg, is_cd = _handle_threshold_alert(
                rule_name, "DISK USAGE", usage, threshold, severity,
                rule.get("cooldown", 300)
            )
            result["is_alert"] = not is_cd
            result["is_cooldown"] = is_cd
            result["alert_msg"] = alert_msg

    # ═══════════════════════════════════════════════
    # PROCESS MONITOR (notify only, no kill)
    # ═══════════════════════════════════════════════

    elif rtype == "process_auto":
        from collectors.process import find_heavy_processes
        cpu_thresh = int(rule.get("cpu_threshold", 80))
        ram_thresh = int(rule.get("ram_threshold", 80))
        wl = rule.get("whitelist", None)
        heavy = find_heavy_processes(cpu_thresh, ram_thresh, wl)

        if heavy:
            result["text"] = f"{len(heavy)} heavy process(es)"
            
            cooldown = rule.get("cooldown", 30)
            last_run = cooldown_memory.get(rule_name, 0)
            now = time.time()

            if now - last_run < cooldown:
                result["is_cooldown"] = True
            else:
                proc_info = "\n".join([
                    f"  - {p['name']} (PID:{p['pid']}) CPU:{p['cpu']}% RAM:{p['ram']}%"
                    for p in heavy
                ])
                result["alert_msg"] = (
                    f"[WARNING] *HEAVY PROCESS DETECTED*\n"
                    f"Rule: {rule_name}\n"
                    f"Found {len(heavy)} process(es):\n{proc_info}"
                )
                result["is_alert"] = True
                cooldown_memory[rule_name] = now
                send_message(result["alert_msg"])
        else:
            result["text"] = "All processes normal"

    # ═══════════════════════════════════════════════
    # SERVICE MONITOR (auto-restart + notify)
    # ═══════════════════════════════════════════════

    elif rtype == "service":
        status = check_service(rule["service_name"])
        result["text"] = f"Status: {status}"

        if status == rule.get("if_status", "inactive"):
            cooldown = rule.get("cooldown", 60)
            last_run = cooldown_memory.get(rule_name, 0)
            now = time.time()

            if now - last_run < cooldown:
                result["is_cooldown"] = True
            else:
                action_cmd = rule.get("action", f"systemctl restart {rule['service_name']}")
                reason = f"Service {rule['service_name']} is {status}"
                try:
                    subprocess.run(action_cmd, shell=True, check=True)
                    result["alert_msg"] = (
                        f"[OK] *AUTO-RESTART SUCCESS*\n"
                        f"Rule: {rule_name}\n"
                        f"Reason: {reason}\n"
                        f"Executed: `{action_cmd}`"
                    )
                except subprocess.CalledProcessError:
                    result["alert_msg"] = (
                        f"[FAIL] *AUTO-RESTART FAILED*\n"
                        f"Rule: {rule_name}\n"
                        f"Reason: {reason}\n"
                        f"Failed: `{action_cmd}`"
                    )

                result["is_alert"] = True
                cooldown_memory[rule_name] = now
                if result["alert_msg"]:
                    send_message(result["alert_msg"])

    # ═══════════════════════════════════════════════
    # LEGACY: process by name (backward compat)
    # ═══════════════════════════════════════════════

    elif rtype == "process":
        from collectors.process import check_process
        is_running = check_process(rule["process_name"])
        status = "running" if is_running else "stopped"
        result["text"] = f"Process: {status}"
        if status == rule.get("if_status", "stopped"):
            result["is_alert"] = True

    return result
