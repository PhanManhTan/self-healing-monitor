# Self-Healing Monitor

A lightweight Python daemon for Linux servers. Monitors system metrics, sends Telegram alerts at configurable thresholds, and auto-restarts crashed services. No database required.

## What It Does

| Module | Behavior | Details |
|--------|----------|---------|
| CPU | Notify only | Alerts at 70%, 85%, 95% |
| RAM | Notify only | Alerts at 70%, 85%, 95% |
| Disk | Notify only | Alerts at 80%, 90%, 95% |
| Process | Notify only | Detects processes with high CPU/RAM usage |
| Service | Auto-restart + notify | Restarts inactive systemd services via `systemctl restart` |

Alert severity scales with threshold level:

- `[WARNING]` — lowest threshold crossed
- `[CRITICAL]` — middle threshold crossed
- `[DANGER]` — highest threshold crossed

Each threshold has its own cooldown. Crossing a higher threshold triggers a new alert even if the lower one is still in cooldown.

## Project Structure

```
self-healing-monitor/
├── main.py              # Dashboard loop — renders live status to terminal
├── config.py            # Loads .env and parses rules.yaml
├── rules.yaml           # All monitoring rules (thresholds, cooldowns, intervals)
├── setup_wizard.py      # Quick setup: default mode or --custom
├── demo_crash.py        # Stress test script (CPU / RAM)
├── collectors/
│   ├── system.py        # check_cpu(), check_memory(), check_disk()
│   ├── service.py       # check_service() — wraps systemctl is-active
│   └── process.py       # find_heavy_processes() — scans process table
├── engine/
│   └── evaluator.py     # Core logic: collect → evaluate → act/notify
└── notifiers/
    └── telegram.py      # Sends alerts via Telegram Bot API
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure Telegram (optional)
cp .env.example .env
# Edit .env — add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# 3. Generate rules.yaml with defaults
python setup_wizard.py

# 4. Run the monitor
python main.py
```

## Setup Wizard

Two modes:

```bash
# Default — auto-configures everything, no questions asked
python setup_wizard.py

# Custom — interactive, override thresholds and pick services
python setup_wizard.py --custom
```

Default mode auto-detects running systemd services and saves immediately.
Custom mode lets you skip modules, change thresholds, and select specific services.

## Configuration

Edit `rules.yaml` directly to fine-tune. Three rule formats:

### Threshold rules (CPU / RAM / Disk) — notify only

```yaml
- name: Monitor CPU
  type: cpu                # cpu | memory | disk
  thresholds: [70, 85, 95] # alert at each level
  cooldown: 60             # seconds between alerts per threshold
  interval: 10             # check every N seconds
```

For disk, add `mount_path`:

```yaml
- name: Monitor Disk
  type: disk
  mount_path: /
  thresholds: [80, 90, 95]
  cooldown: 300
  interval: 60
```

### Process rules — notify only

```yaml
- name: Monitor Processes
  type: process_auto
  cpu_threshold: 80        # notify if any process exceeds this CPU%
  ram_threshold: 80        # notify if any process exceeds this RAM%
  cooldown: 30
  interval: 10
```

### Service rules — auto-restart + notify

```yaml
- name: Monitor nginx
  type: service
  service_name: nginx
  if_status: inactive      # trigger when service is inactive
  action: systemctl restart nginx
  cooldown: 60
  interval: 10
```

## Testing

Run the monitor in one terminal, then stress-test in another:

```bash
# Terminal 1
python main.py

# Terminal 2
python demo_crash.py
```

`demo_crash.py` offers four scenarios:

1. CPU spike — max out all cores
2. RAM spike — allocate 512MB
3. Both — CPU + RAM
4. Quick CPU — 1 core for 30 seconds then auto-stop

The monitor will detect the spike and send a Telegram alert (if configured) or print the event in the dashboard.

## Dashboard

`main.py` renders a live terminal dashboard:

```
Self-Healing Monitor  11:50:23
────────────────────────────────────────

 METRICS
  CPU    ██████░░░░░░░░░░░░░░  28.5% (70/85/95%)
  RAM    ████████████░░░░░░░░  61.2% (70/85/95%)
  DISK   ██████████████░░░░░░  72.0% (80/90/95%)

 PROCESSES
  [OK] All processes normal

 SERVICES
  ● nginx                active
  ● docker               active
  ● mysql                active

 RECENT EVENTS
  11:48:12  [WARNING] *CPU USAGE ALERT*
  11:49:05  [OK] *AUTO-RESTART SUCCESS*

────────────────────────────────────────
Ctrl+C to exit | rules.yaml to configure
```

## Dependencies

- `psutil` — system metrics and process inspection
- `pyyaml` — rules.yaml parsing
- `requests` — Telegram Bot API
- `python-dotenv` — .env loading
