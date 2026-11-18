# AWS Deployment Guide — GTA 6 Cloud Clipping Platform

Yes, hosting the entire platform on **Amazon Web Services (AWS)** is completely supported.

---

## 1. Recommended AWS Architectures

### Option A: Single EC2 Instance with Docker Compose (Recommended)
This is the simplest, most cost-effective option and matches the [infra/docker-compose.yml](file:///c:/Users/olade/Documents/GitHub/gta-clips/infra/docker-compose.yml) setup directly.

- **Compute**: Single EC2 instance (Ubuntu 24.04 LTS).
  - Recommended instance: **`c7g.large`** (2 vCPU, 4 GB RAM, AWS Graviton3) or **`c6i.large`** (2 vCPU, 4 GB RAM, Intel).
  - Why compute-optimized (`c` series): FFmpeg video rendering and Streamlink capture benefit heavily from dedicated CPU performance.
- **Storage**:
  - Root & Scratch Disk: 50–100 GB EBS `gp3` volume (handles temporary 10-minute video segments before 24-hour cleanup).
- **Networking**:
  - Elastic IP (static public IP) attached to the instance.
  - Security Group: Inbound ports `80` (HTTP), `443` (HTTPS), and `22` (SSH restricted to your IP).
- **Estimated Cost**: ~$30–$45 / month (or ~$18–$25 on a 1-year Savings Plan / Spot instance).

### Option B: Fully Managed AWS (Enterprise Scale)
If you prefer AWS to manage high-availability database backups and auto-scaling containers:
- **Containers**: AWS ECS with EC2 or Fargate launch type (API, Worker, Web).
- **Database**: AWS Aurora PostgreSQL Serverless v2 or RDS PostgreSQL (`db.t4g.micro` or `db.t4g.small`).
- **Cache**: AWS ElastiCache for Redis Serverless.
- **Load Balancer**: AWS Application Load Balancer (ALB) with AWS Certificate Manager (ACM) SSL.
- **Estimated Cost**: ~$90–$140 / month.

---

## 2. Cloudflare R2 vs. AWS S3 for Video Clips

The platform uses standard `boto3` in [packages/shared/storage.py](file:///c:/Users/olade/Documents/GitHub/gta-clips/packages/shared/storage.py), so you can use either:

1. **Cloudflare R2 (Recommended)**:
   - **$0 egress fees**: Downloading clips to your dashboard or publishing to TikTok / YouTube Shorts incurs zero bandwidth charges.
   - 10 GB free monthly storage.
2. **AWS S3**:
   - Works immediately by changing `R2_ENDPOINT_URL` to AWS standard S3 endpoint and setting your AWS access keys in `.env`.
   - Keep in mind: AWS S3 charges ~$0.09 per GB for data egress to the public internet.

---

## 3. Step-by-Step EC2 Deployment (Option A)

### Step 1: Launch EC2 Instance
1. Open the [AWS EC2 Console](https://console.aws.amazon.com/ec2).
2. Click **Launch Instance**:
   - **Name**: `gta6-clips-platform`
   - **AMI**: Ubuntu Server 24.04 LTS (HVM), SSD Volume Type (ARM64 for `c7g` or x86_64 for `c6i`).
   - **Instance Type**: `c7g.large` (ARM64) or `c6i.large` (x86_64).
   - **Key Pair**: Select or create an SSH key pair.
   - **Network Settings**:
     - Allow SSH traffic from: `My IP`
     - Allow HTTP traffic from the internet (`0.0.0.0/0`)
     - Allow HTTPS traffic from the internet (`0.0.0.0/0`)
   - **Configure Storage**: 60 GB `gp3` (3000 IOPS, 125 MB/s).

### Step 2: Allocate & Associate Elastic IP
1. In the EC2 sidebar, go to **Network & Security -> Elastic IPs**.
2. Click **Allocate Elastic IP address**.
3. Select the IP, click **Actions -> Associate Elastic IP address**, and choose your instance.

### Step 3: Connect and Deploy
SSH into your instance:
```bash
ssh -i your-key.pem ubuntu@YOUR_ELASTIC_IP
```

Install Docker and Docker Compose:
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
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

Clone the repository and deploy:
```bash
git clone https://github.com/YOUR_USER/gta-clips.git /opt/gta-clips
cd /opt/gta-clips

# Configure environment secrets
cp docs/ENVIRONMENT.example .env
nano .env

# Run deployment script
bash infra/deploy.sh
```

### Step 4: Access Your Dashboard
Open your browser and navigate to:
- `http://YOUR_ELASTIC_IP` or `https://your-custom-domain.com` (pointed to the Elastic IP).
- Default Admin Login: `admin` / `GTA6ClipsPass!2026`.
