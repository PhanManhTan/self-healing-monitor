# Self-Healing Monitor

Simple Python monitor for CPU, RAM, disk, processes and Linux systemd services.
Alerts are sent to Telegram. Inactive services can be restarted automatically.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
python setup.py
python main.py
```

Configure Telegram in `.env`:

```env
CHECK_INTERVAL=1
TELEGRAM_BOT_TOKEN=1234567890:your_bot_token
TELEGRAM_CHAT_ID=your_user_or_group_chat_id
```

Open the bot and send `/start` before running the monitor. The chat ID must be
your user/group ID, not the number before `:` in the bot token.

## Rules

Rules live in `rules.yaml`. Each rule supports its own check interval and alert
cooldown. CPU, RAM, disk and process rules only notify. Service rules notify and
run their configured restart command.

## Logs

The terminal dashboard refreshes in place like the original version. Full
history is appended to `monitor.log` and is not lost when the screen refreshes.

## Crash test

Interactive mode:

```bash
python demo_crash.py
```

Non-interactive mode for CI:

```bash
python demo_crash.py --scenario cpu --duration 20 --workers 2
```

## GitHub Actions

The workflow `.github/workflows/monitor.yml` starts the monitor, runs a bounded
CPU stress test on the same runner, prints a Markdown job summary and uploads
the summary with `monitor.log`. Add repository secrets named
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` if CI should send real Telegram
alerts.
