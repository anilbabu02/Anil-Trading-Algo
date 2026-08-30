#!/bin/bash
set -e

echo '=================================================='
echo 'Deploying ANIL BABU TRADES on Oracle Cloud VM'
echo '=================================================='

if command -v dnf > /dev/null 2>&1; then
    echo '[1/5] Updating Oracle Linux packages...'
    sudo dnf update -y
    sudo dnf install -y python3 python3-pip python3-devel git gcc
elif command -v apt-get > /dev/null 2>&1; then
    echo '[1/5] Updating Ubuntu packages...'
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv git gcc
fi

APP_DIR=./anil_babu_trades
echo '[2/5] Cloning from GitHub...'
git clone https://github.com/anilbabu02/Anil-Trading-Algo.git $APP_DIR || (cd $APP_DIR && git pull origin main)
cd $APP_DIR

echo '[3/5] Setting up Python venv...'
python3 -m venv venv
./venv/bin/pip install upgrade pip
./venv/bin/pip install -r requirements.txt

echo '[4/5] Opening Port 8000 in Firewall...'
if command -v firewall-cmd > /dev/null 2>&1; then
    sudo firewall-cmd --zone=public --add-port=8000/tcp --permanent || true
    sudo firewall-cmd --reload || true
elif command -v ufw > /dev/null 2>&1; then
    sudo ufw allow 8000/tcp || true
fi

echo '[5/5] Starting Algorithmic Trading Server...'
./venv/bin/python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
