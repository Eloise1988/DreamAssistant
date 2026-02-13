# Dream Diary Telegram Bot (Lucid Dream Protocol)

Personal Telegram chat bot for advanced dream journaling, interpretation, and lucid-dream progression.

## Features

- Structured dream entry flow inspired by paper dream diaries
- Multiple sections to keep users engaged and reduce dropout
- MongoDB storage for entries, streaks, and recurring symbols
- Lucid exercise library (stored in MongoDB) with random menu retrieval
- Weekly random exercise reminder (Sunday 09:00 UTC)
- Reality-check reminder 3x/day (07:00, 14:00, 21:00 US Central)
- ChatGPT-powered dream interpretation and adaptive 7-day lucid protocol
- Daily reminder scheduling (`/set_reminder HH:MM` in UTC)

## Tech Stack

- Python 3.10+ (works on Ubuntu 20 with deadsnakes or pyenv)
- `python-telegram-bot` (async bot)
- MongoDB
- OpenAI ChatGPT API

## Ubuntu 20.04 Setup

```bash
sudo apt update
sudo apt install -y software-properties-common curl git build-essential
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev
```

Install MongoDB Community (official repo):

```bash
curl -fsSL https://pgp.mongodb.com/server-7.0.asc | \
  sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/7.0 multiverse" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

sudo apt update
sudo apt install -y mongodb-org
sudo systemctl enable --now mongod
```

## Bot Setup

```bash
cd /Users/charmantaudrey/Desktop/Dreams
python3.10 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default `gpt-4.1-mini`)
- `MONGODB_URI`
- `MONGODB_DB`

Alternative config location (recommended for servers):

```bash
mkdir -p ~/.config
nano ~/.config/dreams.env
```

Example `~/.config/dreams.env`:

```bash
TELEGRAM_BOT_TOKEN=123456:abcDEF_your_token
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=dream_diary
DEFAULT_TIMEZONE=UTC
```

Optional: set custom env file path with `DREAMS_ENV_FILE=/path/to/file.env`.

Run:

```bash
python main.py
```

## Run As System Service (Recommended)

This is the production setup (always on, auto-start at boot, auto-restart on crash).

1. Ensure bot works once manually:

```bash
cd /path/to/Dreams
source .venv/bin/activate
python main.py
```

2. Install the `systemd` service:

```bash
cd /path/to/Dreams
./deploy/systemd/install.sh <linux-user> /path/to/Dreams
```

Example:

```bash
./deploy/systemd/install.sh ubuntu /home/ubuntu/Dreams
```

The service will auto-read env from:

1. `~/.config/dreams.env`
2. `/path/to/Dreams/.env`

3. Verify and monitor:

```bash
sudo systemctl status dream-diary-bot.service
sudo journalctl -u dream-diary-bot.service -f
```

4. Manage service:

```bash
sudo systemctl restart dream-diary-bot.service
sudo systemctl stop dream-diary-bot.service
sudo systemctl start dream-diary-bot.service
```

## Telegram Commands

- `/start` start onboarding and menu
- `/menu` open menu
- `/cancel` cancel active journaling flow
- `/set_reminder HH:MM` set daily reminder (UTC)
- `/clear_reminder` clear reminder

## Engagement Protocol Built In

- Variation by mode: journaling, drill, interpretation, progress, protocol tuning
- Dream-sign mining from recurring symbols
- Progressive difficulty protocol generated from your recent history
- Daily loop: Morning capture -> Day reality checks -> Night intention

## Recommended Next Enhancements

- Timezone-aware reminders per user
- Voice note transcription for rapid wake capture
- Weekly PDF export matching your diary layout
- Multi-agent coach personas (strict, gentle, analytical)
