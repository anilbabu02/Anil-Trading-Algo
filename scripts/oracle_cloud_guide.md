# ☁️ Oracle Cloud Always Free (₹0 Forever) 24/7 Deployment Guide

This guide walks you through deploying your **Anil Babu Trades Algo System** on **Oracle Cloud Always Free Tier** in Mumbai or Hyderabad for **100% FREE (₹0)** forever with **<5ms latency to NSE**.

---

## 📋 Step 1: Create Your Free Oracle Cloud Account
1. Visit: [**https://www.oracle.com/cloud/free/**](https://www.oracle.com/cloud/free/)
2. Click **Start for free**.
3. Select your **Home Region**: Choose **India South (Mumbai)** or **India Central (Hyderabad)**.
4. Complete the sign-up (Oracle requires a debit/credit card for identity verification, but charges **₹0** for Always Free resources).

---

## 🖥️ Step 2: Create Your Free Ubuntu Cloud VM
1. In the Oracle Cloud Console, go to **Compute** $\rightarrow$ **Instances** $\rightarrow$ Click **Create Instance**.
2. **Name**: `anil-trading-algo-vm`
3. **Image**: Choose **Canonical Ubuntu 22.04 LTS** (or 24.04).
4. **Shape**: Choose **Always Free-eligible**:
   - *Option A (Recommended)*: **VM.Standard.A1.Flex (ARM)** with 2 to 4 OCPUs & 12 to 24 GB RAM.
   - *Option B*: **VM.Standard.E2.1.Micro (AMD)** with 1 OCPU & 1 GB RAM.
5. **Networking**: Create new VCN with a **Public IPv4 Address**.
6. **SSH Keys**: Download and save your **Private Key** (`.key` file) to your computer.
7. Click **Create** (Your server will be running in ~60 seconds).

---

## 🛡️ Step 3: Open Port 8000 in Oracle Cloud Firewall
1. Under **Instance details**, click on your **Subnet** link.
2. Click on **Default Security List for...**
3. Under **Ingress Rules**, click **Add Ingress Rules**:
   - **Source CIDR**: `0.0.0.0/0`
   - **IP Protocol**: `TCP`
   - **Destination Port Range**: `8000, 80, 443`
   - **Description**: `Algo Trading Dashboard`
4. Click **Add Ingress Rules**.

---

## 🚀 Step 4: 1-Click Installation (Terminal)
Open your terminal (PowerShell or PuTTY on Windows) and connect to your server:
```bash
ssh -i /path/to/your-private-key.key ubuntu@<YOUR_SERVER_PUBLIC_IP>
```

Once logged in, paste this **single 1-click setup command**:
```bash
curl -sSL https://raw.githubusercontent.com/anilbabu02/Anil-Trading-Algo/main/scripts/setup_oracle_cloud.sh | bash
```

---

## 🎉 Done! Access Your 24/7 Live Algo Dashboard
Your algo engine is now running as a permanent background service:
- 🌐 Open: **`http://<YOUR_SERVER_PUBLIC_IP>:8000`** in your mobile or laptop browser.
- 📱 It will run **24/7/365** continuously even when your home laptop is closed or turned off.

---

## 🔄 Useful Commands on Server:
- View live logs: `sudo docker logs -f anil_babu_trading_algo`
- Restart algo: `sudo docker compose restart`
- Update to latest GitHub code:
  ```bash
  cd ~/Anil-Trading-Algo && git pull && sudo docker compose up -d --build
  ```
