#!/usr/bin/env bash
# ============================================================
#  Personal OPS Bot — Server install script
#  Tested on Ubuntu 22.04 / Debian 12
#  Usage:  bash install.sh
# ============================================================
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/YOUR_USERNAME/YOUR_REPO.git}"
INSTALL_DIR="/opt/opsbot"
SERVICE_NAME="opsbot"
PYTHON="python3"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Personal OPS Bot — installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. System deps ─────────────────────────────────────────
echo "[1/6] Updating system packages…"
apt-get update -qq
apt-get install -y -qq git python3 python3-pip python3-venv curl

# ── 2. Clone or update ─────────────────────────────────────
echo "[2/6] Setting up bot directory…"
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  → Repo exists — pulling latest"
    git -C "$INSTALL_DIR" pull --ff-only
else
    echo "  → Cloning from $REPO_URL"
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# ── 3. Virtual environment ─────────────────────────────────
echo "[3/6] Creating Python venv…"
$PYTHON -m venv venv
source venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  → Dependencies installed"

# ── 4. .env file ───────────────────────────────────────────
echo "[4/6] Configuring .env…"
if [ ! -f .env ]; then
    cat > .env <<'EOF'
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_ID=YOUR_TELEGRAM_USER_ID
API_KEY=YOUR_PANEL_API_KEY
MCP_URL=https://whitelist.soon.it/api/mcp
EOF
    echo "  → .env created — EDIT IT before starting the bot!"
    echo "     nano $INSTALL_DIR/.env"
else
    echo "  → .env already exists — skipping"
fi

# ── 5. Systemd service ─────────────────────────────────────
echo "[5/6] Installing systemd service…"
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Personal OPS Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
echo "  → Service registered: ${SERVICE_NAME}"

# ── 6. Done ────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  Installation complete!"
echo ""
echo "  Next steps:"
echo "  1. Edit .env:   nano $INSTALL_DIR/.env"
echo "  2. Start bot:   systemctl start $SERVICE_NAME"
echo "  3. Check logs:  journalctl -u $SERVICE_NAME -f"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
