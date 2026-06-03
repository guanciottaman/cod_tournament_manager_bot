#!/bin/bash

set -e

echo "========================================"
echo "  CoD Tournament Manager Bot Installer"
echo "========================================"

# update system
echo "[1/6] Aggiorno il sistema..."
apt update && apt upgrade -y

# dependencies
echo "[2/6] Installo python..."
apt install -y python3 python3-pip python3-venv git

# folder
echo "[3/6] Creo la cartella..."
mkdir -p /opt/codm_bot
cd /opt/codm_bot

# repo
echo "[4/6] Clono il repository..."
git clone https://github.com/guanciottaman/cod_tournament_manager_bot.git .

# venv
echo "[5/6] Creo l'ambiente virtuale..."
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# TOKEN INPUT
echo "[6/6] Configurazione Bot"

TOKEN=${TOKEN:-}

if [ -z "$TOKEN" ]; then
    if [ -t 0 ]; then
        # terminale interattivo
        read -s -p "Inserisci il TOKEN del bot: " TOKEN
        echo ""
    else
        echo "ERRORE: Input interagibile non disbonibile. Esegui con TOKEN=xxxx bash install.sh"
        exit 1
    fi
fi

cat <<EOF > .env
TOKEN=$TOKEN
EOF

echo "File .env creato."

# systemd service
echo "Creo il servizio systemd..."

cat <<EOF > /etc/systemd/system/codm_bot.service
[Unit]
Description=CoD Tournament Manager Bot
After=network.target

[Service]
WorkingDirectory=/opt/codm_bot
ExecStart=/opt/codm_bot/venv/bin/python main.py
Restart=always
RestartSec=5
EnvironmentFile=/opt/codm_bot/.env

[Install]
WantedBy=multi-user.target
EOF

# enable service
echo "Avvio il bot..."

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable codm_bot
systemctl start codm_bot

echo "============================"
echo " Bot installato e avviato!"
echo "============================"