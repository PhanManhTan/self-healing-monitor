import os
import psutil


def check_process(process_name: str) -> bool:
    """Check if any process matching the given name is currently running."""
    try:
        for proc in psutil.process_iter(['name', 'cmdline']):
            # Check process executable name
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                return True
            # Check command line arguments (e.g. "python my_script.py")
            if proc.info['cmdline'] and process_name.lower() in ' '.join(proc.info['cmdline']).lower():
                return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
        
    return False


# System-critical processes that should NEVER be killed
DEFAULT_WHITELIST = [
    "systemd", "init", "sshd", "bash", "sh", "zsh", "login",
    "kernel", "kthread", "dbus", "cron", "crond", "rsyslog",
    "NetworkManager", "udevd", "agetty", "sudo", "journald",
    "python3", "python",  # Avoid killing the monitor itself
]


def find_heavy_processes(cpu_threshold: int = 80, ram_threshold: int = 80, whitelist: list = None) -> list:
    """
    Scan all running processes and find ones exceeding CPU or RAM thresholds.
    
    Returns a list of dicts: [{'pid', 'name', 'cpu', 'ram', 'cmdline'}, ...]
    
    Note: cpu_percent() returns meaningful values from the 2nd call onwards
    since it compares CPU times between calls. The daemon loop ensures accuracy.
    """
    if whitelist is None:
        whitelist = DEFAULT_WHITELIST

    my_pid = os.getpid()
    whitelist_lower = [w.lower() for w in whitelist]

    heavy = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cmdline']):
        try:
            pid = proc.info['pid']
            name = proc.info['name'] or ""

            # Skip our own process, PID 0/1/2, and whitelisted processes
            if pid == my_pid or pid <= 2:
                continue
            if name.lower() in whitelist_lower:
                continue

            cpu = proc.cpu_percent(interval=None)
            ram = proc.info['memory_percent'] or 0

            if cpu >= cpu_threshold or ram >= ram_threshold:
                heavy.append({
                    'pid': pid,
                    'name': name,
                    'cpu': round(cpu, 1),
                    'ram': round(ram, 1),
                    'cmdline': ' '.join(proc.info['cmdline'] or [])[:120]
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return heavy


def kill_process(pid: int) -> bool:
    """
    Kill a process by PID. 
    Tries SIGTERM first (graceful), then SIGKILL after 5s timeout.
    Returns True if successful.
    """
    try:
        proc = psutil.Process(pid)
        proc.terminate()  # SIGTERM - graceful shutdown
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()  # SIGKILL - force kill
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
