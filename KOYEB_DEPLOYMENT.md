# Koyeb Deployment Guide

This guide shows how to deploy the Scheduler API to Koyeb with a persistent database using Docker.

## Prerequisites

- Koyeb account (sign up at [koyeb.com](https://www.koyeb.com))
- GitHub account with your repository pushed

## Step 1: Push to GitHub

Ensure your latest changes are pushed to GitHub:

```bash
git add .
git commit -m "Migration to platform-agnostic setup for Koyeb"
git push origin main
```

## Step 2: Deploy to Koyeb

1. Go to your [Koyeb Dashboard](https://app.koyeb.com) and click **"Create Service"**.
2. Select **"GitHub"** as the deployment method.
3. Select your repository and the **"main"** branch.
4. Koyeb will automatically detect the `Dockerfile`.

## Step 3: Configure Persistent Storage

Koyeb supports persistent storage via Volumes.

1. In the service configuration, find the **"Storage"** section.
2. Click **"Add Volume"**.
3. Set **Mount Path:** `/data` (this will match our `DATA_PATH` configuration).
4. Select a size (e.g., 1GB is more than enough for SQLite).

## Step 4: Set Environment Variables

In the **"Environment Variables"** section, add the following:

| Variable | Value | Description |
|----------|-------|-------------|
| `DATA_PATH` | `/data` | Path to the persistent volume mount |
| `ADMIN_USERNAME` | `your_admin` | (Optional) Desired admin username |
| `ADMIN_PASSWORD` | `your_pass` | (Optional) Desired admin password |
| `PORT` | `8000` | Koyeb sets this, but ensure it matches our EXPOSE 8000 |

> [!NOTE]
> If you don't set `ADMIN_USERNAME` and `ADMIN_PASSWORD`, the defaults will be `admin` / `admin123`. **Change these immediately after deployment!**

## Step 5: Finish and Deploy

1. Click **"Deploy"**.
2. Koyeb will build the Docker image and start the service.
3. Once the service is healthy, you'll receive a public URL (e.g., `https://your-service-name.koyeb.app`).

## Accessing Your App

- **Admin Dashboard:** `https://your-service-name.koyeb.app/admin`
- **API Endpoints:** `https://your-service-name.koyeb.app/schedule/json` (etc.)

## Local Verification

Before pushing, you can verify the setup locally:

```bash
# Set environment variables for testing
export DATA_PATH=./test_data
export ADMIN_USERNAME=test_admin
export ADMIN_PASSWORD=test_pass

# Run setup
mkdir -p ./test_data
python server_setup.py

# Start server
uvicorn api_scheduler:app --host 0.0.0.0 --port 8000
```
