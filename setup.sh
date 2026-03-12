#!/bin/bash
# =====================================================
# Script de provisioning de la VM
# Usage: setup.sh <storage_account> <storage_key> <container_name> <username>
# =====================================================

STORAGE_ACCOUNT="$1"
STORAGE_KEY="$2"
CONTAINER_NAME="$3"
USERNAME="$4"

APP_DIR="/home/${USERNAME}/app"

echo "==> Attente de la libération du verrou apt (peut prendre quelques minutes)..."
for i in $(seq 1 60); do
  if ! fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 && \
     ! fuser /var/lib/apt/lists/lock >/dev/null 2>&1 && \
     ! fuser /var/cache/apt/archives/lock >/dev/null 2>&1; then
    break
  fi
  echo "  Verrou apt actif, attente... ($i/60)"
  sleep 10
done

echo "==> Mise à jour du système..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y || true
apt-get install -y python3 python3-pip python3-venv

echo "==> Création de l'environnement virtuel..."
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate

echo "==> Installation des dépendances Python..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Création du fichier .env..."
cat > "$APP_DIR/.env" <<EOF
AZURE_STORAGE_ACCOUNT=${STORAGE_ACCOUNT}
AZURE_STORAGE_KEY=${STORAGE_KEY}
AZURE_CONTAINER_NAME=${CONTAINER_NAME}
EOF

echo "==> Création du service systemd flask-app..."
cat > /etc/systemd/system/flask-app.service <<EOF
[Unit]
Description=Flask Cloud App
After=network.target

[Service]
User=${USERNAME}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/gunicorn --bind 0.0.0.0:5000 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "==> Démarrage du service flask-app..."
systemctl daemon-reload
systemctl enable flask-app
systemctl start flask-app

echo "==> Provisioning terminé ! L'application est accessible sur le port 5000."
