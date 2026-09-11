import psutil

def check_disk(mount_path: str) -> int:
    """Check disk usage percentage."""
    try:
        usage = psutil.disk_usage(mount_path)
        return int(usage.percent)
    except Exception:
        return 0

def check_cpu() -> int:
    """Check total CPU usage percentage."""
    return int(psutil.cpu_percent(interval=0.5))

def check_memory() -> int:
    """Check total RAM usage percentage."""
    return int(psutil.virtual_memory().percent)
