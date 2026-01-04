# Vercel Deployment Guide

This guide shows how to deploy the Scheduler API to **Vercel** with **Supabase** for persistence.

## Prerequisites

- Vercel account
- Supabase account (with the project we set up earlier)
- GitHub account with your repository pushed

## Step 1: Push to GitHub

Ensure your latest changes (including `vercel.json`) are pushed:

```bash
git add .
git commit -m "Add Vercel deployment configuration"
git push origin main
```

## Step 2: Deploy to Vercel

1. Go to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **"Add New..."** > **"Project"**.
3. Import your GitHub repository.
4. **Environment Variables**:
   In the "Environment Variables" section, add:
   - `DATABASE_URL`: Your Supabase URI (e.g., `postgresql://postgres.[ID]:[PASS]@...`)
   - `ADMIN_USERNAME`: (Optional)
   - `ADMIN_PASSWORD`: (Optional)

5. Click **"Deploy"**.

6. **Analytics & Speed Insights**:
   - Go to your project dashboard on Vercel.
   - Click on the **"Analytics"** tab and click **"Enable"**.
   - Click on the **"Speed Insights"** tab and click **"Enable"**.
   - The app is already configured with the necessary script tags in `static/index.html`.

## Step 3: Access Your App

Vercel will provide a URL like `https://scheduler-api.vercel.app`.
- **Admin Dashboard**: `https://scheduler-api.vercel.app/admin`
- **Static Files**: Vercel will serve your `static/` folder based on the FastAPI mounting.

## Troubleshooting

- **Serverless Limits**: Vercel has a 10-second timeout for serverless functions on the Free tier. If you are running 30-volunteer optimizations, they might time out. The standard greedy algorithm (`/schedule/json`) will work perfectly.
- **Environment Variables**: Ensure `DATABASE_URL` is set correctly in the Vercel project settings, not just locally.
