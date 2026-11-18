# Complete Step-by-Step AWS Setup Guide

From brand-new AWS account to a fully working cloud clipping platform.

---

## Step 1: Create Your AWS Account

1. Go to [aws.amazon.com](https://aws.amazon.com) and click **Create an AWS Account**.
2. Enter your email and a name for your account, then click **Verify email address**.
3. Enter the verification code sent to your email and set a strong password.
4. Select **Personal** account type, fill in your contact information, and click **Continue**.
5. Enter your credit or debit card details (AWS charges a small temporary authorization to verify the card).
6. Complete the SMS or phone call identity verification.
7. Choose the **Basic Support (Free)** plan and complete registration.
8. Sign in to the [AWS Management Console](https://console.aws.amazon.com) using your root email and password.

*(Safety Tip: In the top search bar, type **IAM**, click **Add MFA**, and link Google Authenticator on your phone to protect your account.)*

---

## Step 2: Create an SSH Key Pair (To Log In to Your Server)

1. In the top search bar, type **EC2** and press Enter.
2. In the left menu, scroll down to **Network & Security** and click **Key Pairs**.
3. Click the orange **Create key pair** button in the top right.
4. Set:
   - **Name**: `gta-clips-key`
   - **Key pair type**: `RSA`
   - **Private key file format**: `.pem` (works on Windows, Mac, and Linux)
5. Click **Create key pair**.
6. Your browser will download `gta-clips-key.pem`. Move it to an easy-to-find folder (like your `Downloads` or `Documents` folder).

---

## Step 3: Launch Your Cloud Server (EC2)

1. In the EC2 console, click **Instances** on the left menu, then click the orange **Launch instances** button.
2. Fill in the launch form:
   - **Name**: `gta-clips-server`
   - **Application and OS Images**: Click **Ubuntu**, then select **Ubuntu Server 24.04 LTS (HVM)**, Architecture: **64-bit (x86)**.
   - **Instance type**: Choose **`c6i.large`** (2 vCPUs, 4 GB RAM) for best video rendering performance, or **`t3.large`** for low-cost testing.
   - **Key pair (login)**: Select the `gta-clips-key` you created in Step 2.
3. Under **Network settings**, click **Edit** (or check the boxes directly):
   - Check **Allow SSH traffic from**: `Anywhere` (or `My IP` for extra security).
   - Check **Allow HTTP traffic from the internet** (Port 80).
   - Check **Allow HTTPS traffic from the internet** (Port 443).
4. Under **Configure storage**:
   - Change the disk size from `8` GiB to **`60` GiB** (Storage type: `gp3`).
   *(This gives your server plenty of temporary scratch room to record 10-minute livestream chunks before the 24-hour cleanup runs).*
5. Click the orange **Launch instance** button at the bottom right.
6. Wait 1–2 minutes until the instance state shows **Running**.

---

## Step 4: Attach a Static Public IP (Elastic IP)

AWS instances change public IPs if restarted. An Elastic IP keeps your server address permanent.

1. In the left EC2 menu, click **Elastic IPs** (under **Network & Security**).
2. Click **Allocate Elastic IP address**, leave defaults, and click **Allocate**.
3. Select your new IP address checkbox, click the **Actions** dropdown at the top, and select **Associate Elastic IP address**.
4. In the **Instance** field, pick your `gta-clips-server`.
5. Click **Associate**. Note down this IP address (e.g., `3.120.45.67`).

---

## Step 5: Connect to Your Cloud Server

Open **PowerShell** (on Windows) or **Terminal** (on Mac/Linux) on your computer.

Navigate to where you saved your `.pem` key:
```powershell
cd ~/Downloads
```

On Windows PowerShell, set the key permissions and SSH in (replace `3.120.45.67` with your Elastic IP):
```powershell
ssh -i gta-clips-key.pem ubuntu@3.120.45.67
```
*(If prompted: `Are you sure you want to continue connecting (yes/no)?`, type `yes` and press Enter).*

You are now inside your cloud Linux server!

---

## Step 6: Install Docker on the Cloud Server

Paste this single block into your server terminal to install Docker and Git:

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker ubuntu
newgrp docker
```

Test that Docker is ready:
```bash
docker --version
docker compose version
```

---

## Step 7: Clone This Project on the Server

Clone your repository into `/opt/gta-clips`:

```bash
sudo git clone https://github.com/YOUR_GITHUB_USERNAME/gta-clips.git /opt/gta-clips
sudo chown -R ubuntu:ubuntu /opt/gta-clips
cd /opt/gta-clips
```

---

## Step 8: Configure Environment Secrets

Create your production configuration from the example file:

```bash
cp docs/ENVIRONMENT.example .env
nano .env
```

Set these basic settings inside the file:
```env
APP_ENV=production
PUBLIC_BASE_URL=http://YOUR_ELASTIC_IP
PUBLIC_DOMAIN=YOUR_ELASTIC_IP
SESSION_SECRET=make_up_a_long_random_secret_string_here
```

*(You can add your live keys for Twitch, Deepgram, Groq, Cloudflare R2, and Zernio now, or leave them empty to test with the built-in fallback modes).*

Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit `nano`.

---

## Step 9: Launch the Platform

Run the automated deployment script:

```bash
bash infra/deploy.sh
```

This will automatically:
1. Build the API container, Worker container, and Web Dashboard container.
2. Start PostgreSQL 16, Redis 7, and the Caddy web server.
3. Set up the database tables and create the default admin user.
4. Verify the health check endpoint.

---

## Step 10: Open Your Web Dashboard

1. Open your web browser on your computer.
2. Go to:
   ```text
   http://YOUR_ELASTIC_IP
   ```
3. Sign in with the default administrator credentials:
   - **Username**: `admin`
   - **Password**: `GTA6ClipsPass!2026`
4. You are in! You can now:
   - Click **Add Streamer** to add channels to monitor.
   - Click **Check Live** to probe channels immediately.
   - Watch the AI detect highlights, edit vertical 9:16 clips, and queue them for review.
   - Preview videos in the mobile frame, tweak titles, and approve them for social publishing.
