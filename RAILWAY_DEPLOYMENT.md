# Railway Deployment Guide (GitHub Push)

This guide shows how to deploy the Scheduler API to Railway with a persistent database using GitHub integration. Just push to GitHub and Railway will automatically deploy!

## Prerequisites

- GitHub account
- Railway account (free at [railway.app](https://railway.app))
- Your code pushed to a GitHub repository

## Step 1: Push to GitHub

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Add API key authentication system"

# Create repo on GitHub and push
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

## Step 2: Deploy to Railway

1. Go to [railway.app](https://railway.app) and sign in
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. **Authorize Railway** to access your GitHub account
5. **Select your repository** from the list
6. Railway will automatically detect the `Dockerfile` and start deploying ✨

## Step 3: Configure Persistent Database

Railway provides persistent storage through volumes. Here's how to set it up:

### Finding Volumes in Railway

1. Once deployed, click on your **service** (the box with your app name)
2. Look for the **"Data"** or **"Storage"** tab in the left sidebar
3. If you don't see "Volumes", try these alternatives:

**Option A: Railway Volumes (Recommended)**

If available on your plan:
1. Click **"Volumes"** in the service menu
2. Click **"New Volume"** or **"+ Volume"**
3. Set **Mount Path:** `/data`
4. Click **"Add"** or **"Deploy"**

**Option B: Use PostgreSQL for Persistence (Alternative)**

If volumes aren't available, you can use Railway's free PostgreSQL for storing the database:

1. In your project, click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway will provision a Postgres database
3. Add this environment variable to your service:
   ```
   USE_POSTGRES=true
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   ```
4. Your app will automatically use Postgres instead of SQLite

**Option C: Local SQLite (Testing Only)**

For testing only (database will reset on redeploy):
- Skip this step
- Database will be stored in the container (non-persistent)
- Good for testing, but you'll lose data on each deploy

### ⚠️ Important Note

If you can't find Volumes, you're likely on Railway's Hobby plan where volumes may require additional setup or billing. The PostgreSQL option (B) works on all plans and is actually more robust for production use!

## Step 4: Set Environment Variables

Go to the **"Variables"** tab and add these:

### Required Variables

```
RAILWAY_VOLUME_MOUNT_PATH=/data
```

### Optional (Recommended for Security)

```
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_secure_password_here
```

If you don't set `ADMIN_USERNAME` and `ADMIN_PASSWORD`, the defaults will be used:
- Username: `admin`
- Password: `admin123`

⚠️ **Change these after first login for security!**

## Step 5: Redeploy (if needed)

After adding the volume and environment variables:

1. Click **"Deployments"** tab
2. Click the **⋮** menu on the latest deployment
3. Click **"Redeploy"**

Or simply push a new commit to GitHub and it will auto-deploy!

## How It Works

When Railway deploys your app:

1. **Builds** using your `Dockerfile`
2. **Runs** `start.sh` which:
   - Executes `railway_setup.py` (creates admin account automatically)
   - Starts the API server
3. **Database** is stored in `/data/api_keys.db` on the persistent volume
4. **Admin account** is created from environment variables (or defaults)

## Accessing Your Deployed App

1. Railway will provide a public URL like `https://your-app.up.railway.app`
2. Access the admin dashboard at: `https://your-app.up.railway.app/admin`
3. Login with your credentials
4. Generate API keys and start using the API!

## Future Updates

To deploy updates, just push to GitHub:

```bash
git add .
git commit -m "Update API"
git push
```

Railway will automatically:
- Pull the latest code
- Rebuild the Docker image
- Redeploy the app
- **Keep your database** (thanks to the volume!)

## What's Already Configured

Your project has these files ready for Railway:

✅ **Dockerfile** - Builds the Python environment  
✅ **railway.json** - Railway configuration  
✅ **start.sh** - Startup script (creates admin + starts server)  
✅ **railway_setup.py** - Auto-creates admin from env vars  
✅ **auth.py** - Uses `/data` path when `RAILWAY_VOLUME_MOUNT_PATH` is set  
✅ **requirements.txt** - All dependencies listed  

Everything is ready - **just push to GitHub and deploy!**

## Database Backup

To backup your database:

```bash
# Using Railway CLI (optional)
railway login
railway link
railway run cat /data/api_keys.db > backup.db
```

Or download via Railway's file browser (coming soon in Railway UI).

## Troubleshooting

### Database resets after deployment
- Verify volume is mounted at `/data`
- Check `RAILWAY_VOLUME_MOUNT_PATH=/data` is set in variables

### Can't login to admin
- Check Railway logs for the admin creation message
- Verify `ADMIN_USERNAME` and `ADMIN_PASSWORD` are set correctly
- Try the defaults: `admin` / `admin123`

### API returns errors
- Check Railway logs: click "Deployments" → "View Logs"
- Verify all files are committed to GitHub
- Ensure `PORT` environment variable is available (Railway sets this automatically)

## Cost

Railway Hobby Plan ($5/month):
- 500 hours compute
- 100 GB bandwidth
- 1 GB storage (perfect for SQLite)
- Custom domains + HTTPS

Your API should stay well within these limits!

