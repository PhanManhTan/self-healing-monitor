import psutil


def check_disk(mount_path: str) -> int:
    return int(psutil.disk_usage(mount_path).percent)


def check_cpu() -> int:
    return int(psutil.cpu_percent(interval=0.5))


def check_memory() -> int:
    return int(psutil.virtual_memory().percent)
