import os

import psutil


DEFAULT_WHITELIST = {
    "systemd", "init", "sshd", "bash", "sh", "login", "dbus",
    "cron", "crond", "sudo", "python", "python3",
}


def find_heavy_processes(
    cpu_threshold: int = 80,
    ram_threshold: int = 80,
    whitelist: list[str] | None = None,
) -> list[dict]:
    """Return processes that exceed the CPU or RAM threshold."""
    ignored = {name.lower() for name in (whitelist or DEFAULT_WHITELIST)}
    heavy = []

    for process in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = process.info
            name = info["name"] or "unknown"
            if info["pid"] == os.getpid() or name.lower() in ignored:
                continue

            cpu = round(info["cpu_percent"] or 0, 1)
            ram = round(info["memory_percent"] or 0, 1)
            if cpu >= cpu_threshold or ram >= ram_threshold:
                heavy.append({"pid": info["pid"], "name": name, "cpu": cpu, "ram": ram})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return heavy
