#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <linux-user> <absolute-project-dir>"
  echo "Example: $0 ubuntu /home/ubuntu/Dreams"
  exit 1
fi

BOT_USER="$1"
BOT_DIR="$2"
SERVICE_NAME="dream-diary-bot.service"
SRC_TEMPLATE="$BOT_DIR/deploy/systemd/dream-diary-bot.service"
TMP_FILE="/tmp/${SERVICE_NAME}"

if [[ ! -f "$SRC_TEMPLATE" ]]; then
  echo "Template not found: $SRC_TEMPLATE"
  exit 1
fi

if [[ ! -x "$BOT_DIR/.venv/bin/python" ]]; then
  echo "Missing virtualenv python at $BOT_DIR/.venv/bin/python"
  echo "Create it first: python3.10 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [[ ! -f "$BOT_DIR/.env" ]]; then
  echo "Missing $BOT_DIR/.env"
  exit 1
fi

sed -e "s|__BOT_USER__|$BOT_USER|g" -e "s|__BOT_DIR__|$BOT_DIR|g" "$SRC_TEMPLATE" > "$TMP_FILE"

sudo cp "$TMP_FILE" "/etc/systemd/system/$SERVICE_NAME"
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"

echo "Installed and started $SERVICE_NAME"
echo "Check status with: sudo systemctl status $SERVICE_NAME"
echo "Follow logs with: sudo journalctl -u $SERVICE_NAME -f"
