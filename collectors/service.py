import subprocess


def check_service(service_name: str) -> str:
    """Return a systemd service status."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() or "inactive"
    except (OSError, subprocess.SubprocessError):
        return "unsupported"
