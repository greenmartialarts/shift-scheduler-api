# Koyeb Deployment Guide (Free Tier + Supabase)

This guide shows how to deploy the Scheduler API to Koyeb's **Free Tier** using **Supabase** for persistent storage.

## Prerequisites

- Koyeb account (Free Tier)
- Supabase account (Free Project)
- GitHub account with your repository pushed

## Step 1: Push to GitHub

Ensure your latest changes are pushed to GitHub:

```bash
git add .
git commit -m "Support Supabase for free persistence on Koyeb"
git push origin main
```

## Step 2: Get your Supabase Connection String

1. Go to your [Supabase Dashboard](https://supabase.com/dashboard).
2. Select your project (**SchedulerDB-Production** or similar).
3. Go to **Project Settings** > **Database**.
4. Find the **Connection string** section, select **URI**, and copy it.
   - It should looks like: `postgresql://postgres.[YOUR-ID]:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres`
   - **Important:** Make sure to replace `[YOUR-PASSWORD]` with your actual Supabase database password.

## Step 3: Create Koyeb Service (Free Tier)

1. Go to [Koyeb Dashboard](https://app.koyeb.com) and click **"Create Service"**.
2. Select **"GitHub"** and your repository.
3. **Build Options**:
   - Select **Dockerfile**.
   - Keep all defaults (no overrides needed).
4. **Instance**:
   - Select **CPU Eco** > **Free**.
   - Choose a region (e.g., Frankfurt or Washington, D.C.).
5. **Storage**:
   - **DO NOT** add a Volume (Volumes are not supported on the Free tier).

## Step 4: Set Environment Variables

In the **"Environment Variables"** section, add the following:

| Variable | Value | Description |
|----------|-------|-------------|
| `DATABASE_URL` | `postgresql://...` | Your Supabase URI (from Step 2) |
| `ADMIN_USERNAME` | `your_admin` | (Optional) Desired admin username |
| `ADMIN_PASSWORD` | `your_pass` | (Optional) Desired admin password |

> [!IMPORTANT]
> The `DATABASE_URL` is what tells the application to use Supabase instead of a local SQLite file. This ensures your data survives redeployments on the Free tier.

## Step 5: Deploy

1. Click **"Deploy"**.
2. Once the service is healthy, access your admin dashboard at:
   `https://[your-service-name].koyeb.app/admin`

## Troubleshooting

- **Database Errors**: Check your `DATABASE_URL`. Ensure the password is correct and there are no special characters that might need encoding.
- **Login fails**: Check Koyeb logs to see if the admin account was created successfully on the first run.
