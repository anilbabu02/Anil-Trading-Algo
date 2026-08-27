#!/bin/bash
# ==============================================================================
# Anil Babu Trades Algo System - Oracle Cloud Always Free Automated Setup Script
# ==============================================================================

set -e

echo "🚀 [1/5] Updating system packages..."
sudo apt-get update -y && sudo apt-get upgrade -y

echo "📦 [2/5] Installing Docker & Docker Compose..."
sudo apt-get install -y ca-certificates curl gnupg lsb-release git

# Add Docker's official GPG key & repo
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Enable Docker on startup
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

echo "🛡️ [3/5] Configuring Oracle Linux Firewall (Opening Port 8000 & 80/443)..."
# Oracle Cloud Ubuntu VMs use iptables by default; open ingress port 8000
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save || true

echo "📂 [4/5] Preparing Trading Engine Repository..."
APP_DIR="$HOME/Anil-Trading-Algo"
if [ -d "$APP_DIR" ]; then
    echo "Updating existing repository in $APP_DIR..."
    cd "$APP_DIR"
    git pull origin main
else
    echo "Cloning repository from GitHub..."
    git clone https://github.com/anilbabu02/Anil-Trading-Algo.git "$APP_DIR"
    cd "$APP_DIR"
fi

mkdir -p data

echo "🐳 [5/5] Building & Launching Algo Trading Docker Container..."
sudo docker compose down || true
sudo docker compose up -d --build

echo "=============================================================================="
echo "🎉 SUCCESS: Anil Babu Trades Algo System is now LIVE 24/7 on Oracle Cloud!"
echo "🌐 Access your Dashboard at: http://$(curl -s ifconfig.me):8000"
echo "=============================================================================="
