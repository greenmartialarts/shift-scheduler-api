# Volunteer Scheduler API

A FastAPI-based service for automatically assigning volunteers to shifts based on availability, group requirements, and time constraints.

## Features

- **Automatic Shift Assignment**: Intelligently assigns volunteers to shifts while respecting constraints
- **Multiple Optimization Strategies**: Choose from three strategies to optimize different goals
- **Group-Based Requirements**: Specify required volunteer groups for each shift
- **Time Conflict Detection**: Prevents overlapping shift assignments
- **Capacity Management**: Respects maximum hours per volunteer
- **Flexible Input**: Supports both JSON and CSV input formats
- **Detailed Reporting**: Generates assignment reports and identifies unfilled shifts

## 🚀 Quick Start for Developers

If you want to integrate this scheduler into your own website or application, please refer to our:

👉 **[API Integration Guide](./API_INTEGRATION_GUIDE.md)**

This guide includes:
- How to request an API key
- Detailed JSON/CSV schemas
- JavaScript implementation examples
- Full request/reponse demonstrations

---

## Try the API Here :
https://shift-scheduler-api-xi.vercel.app/docs

## 🔐 API Key Authentication

**All scheduler endpoints now require API key authentication for security and rate limiting.**

### Initial Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create Master Admin Account**
   ```bash
   python setup_admin.py
   ```
   This will prompt you to create a username and password for the admin dashboard.

3. **Start the Server**
   ```bash
   uvicorn api_scheduler:app --reload
   ```

4. **Access Admin Dashboard**
   - Navigate to: `http://localhost:8000/admin`
   - Login with your credentials
   - Generate your first API key

### Using the Admin Dashboard

The admin dashboard provides a modern web interface for managing API keys:

- **Generate API Keys**: Create new keys with custom names and rate limits
- **View All Keys**: See all active keys and their usage
- **Update Rate Limits**: Adjust the daily request limit for any key (default: 10,000/day)
- **Revoke Keys**: Instantly disable compromised or unused keys
- **Monitor Usage**: Track request counts per key

### Making Authenticated API Requests

Include your API key in the `Authorization` header:

```bash
curl -X POST "http://localhost:8000/schedule/json" \
  -H "Authorization: Bearer sk_YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d @schedule_request.json
```

**Python Example:**
```python
import requests

headers = {
    'Authorization': 'Bearer sk_YOUR_API_KEY_HERE',
    'Content-Type': 'application/json'
}

response = requests.post(
    'http://localhost:8000/schedule/json',
    headers=headers,
    json=your_schedule_data
)
```

### Rate Limiting

Each API key has a configurable daily rate limit (default: 10,000 requests/day). When exceeded, you'll receive a `429 Too Many Requests` response:

```json
{
  "detail": "Rate limit exceeded. Current: 10000/10000 requests today."
}
```

Rate limits reset at midnight UTC daily.



## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# Clone the repository
git clone https://github.com/greenmartialarts/shift-scheduler-api
cd shift-scheduler-api

# Install dependencies
pip install -r requirements.txt

# Or use the setup script (one command)
./setup.sh
```

## Running the Server

### Local Development
```bash
# With auto-reload (development)
uvicorn api_scheduler:app --reload
```

### Production
```bash
# Without auto-reload
uvicorn api_scheduler:app
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI) is available at `http://localhost:8000/docs`

### Deploying to Railway

This project is configured for deployment on [Railway](https://railway.app):

**Option 1: Using Railway CLI (Quickest)**
```bash
# Install Railway CLI: https://docs.railway.app/guides/cli
npm install -g @railway/cli

# Login and deploy
railway login
railway up
```

**Option 2: Using GitHub Integration**
1. Create a free account at https://railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Select your repository
4. Railway automatically detects the `Dockerfile` and deploys
5. Your API will be live at the generated Railway URL

**Environment Variables** (Railway sets automatically):
- `PORT`: Automatically set by Railway (default 8000)

The `Dockerfile` and `railway.json` handle all configuration automatically!

## 📖 Documentation

For detailed technical documentation, including endpoint schemas, error handling, and example interactions, please see:

- [API Integration Guide](./API_INTEGRATION_GUIDE.md)
- [Admin Master Key Setup](./WALKTHROUGH.md) (Administrative access)

## Project Structure

- `scheduler.py`: Core scheduling logic with volunteer and shift classes
- `api_scheduler.py`: FastAPI application and HTTP endpoints

## License

MIT
