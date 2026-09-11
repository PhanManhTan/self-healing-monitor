import subprocess

def check_service(service_name: str) -> str:
    """Check the status of a systemd service."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True, text=True
        )
        status = result.stdout.strip()
        return status if status else "inactive"
    except Exception:
        return "unknown"
