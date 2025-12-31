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

## Optimization Strategies

The scheduler supports three optimization strategies to meet different scheduling goals:

### 1. `minimize_unfilled` (Default)
**Goal**: Fill as many shift positions as possible

- Uses greedy algorithm prioritizing volunteers with fewest hours
- Maintains backward compatibility with existing implementations
- **Best for**: Ensuring maximum shift coverage

### 2. `maximize_fairness`
**Goal**: Distribute hours evenly across all volunteers

- Balances workload by consistently selecting least-loaded volunteers
- Reduces variance in hours assigned between volunteers
- May result in slightly more unfilled shifts to achieve fairness
- **Best for**: Ensuring equitable work distribution

### 3. `minimize_overtime`
**Goal**: Prioritize volunteers with most available capacity

- Assigns volunteers furthest from their max_hours limits first
- Helps prevent volunteers from exceeding hour limits
- Reduces burnout risk
- **Best for**: Managing volunteer capacity and preventing overwork

### How to Specify Strategy

**JSON Endpoint**: Include `strategy` in request body (optional, defaults to `minimize_unfilled`)
```json
{
  "volunteers": [...],
  "shifts": [...],
  "strategy": "maximize_fairness"
}
```

**CSV Endpoint**: Add `strategy` as a query parameter (optional, defaults to `minimize_unfilled`)
```bash
curl -X POST "http://localhost:8000/schedule/csv?strategy=minimize_overtime" \
  -F "volunteers_file=@volunteers.csv" \
  -F "shifts_file=@shifts.csv"
```

## Try the API Here :
https://shift-scheduler-api-production.up.railway.app/docs

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

## API Endpoints

### 1. Schedule via JSON

**Endpoint**: `POST /schedule/json`

**Description**: Accepts volunteer and shift data in JSON format and returns shift assignments.

**Request Body**:
```json
{
  "volunteers": [
    {
      "id": "v1",
      "name": "John Doe",
      "group": "Delegates",
      "max_hours": 8.0
    }
  ],
  "shifts": [
    {
      "id": "s1",
      "start": "2025-12-01T09:00",
      "end": "2025-12-01T11:00",
      "required_groups": {
        "Delegates": 2,
        "Adults": 2
      },
      "allowed_groups": ["Delegates", "Adults"],
      "excluded_groups": null
    }
  ],
  "strategy": "minimize_unfilled"
}
```

**Note**: The `strategy` field is optional and defaults to `"minimize_unfilled"`. Valid values: `"minimize_unfilled"`, `"maximize_fairness"`, `"minimize_overtime"`.

**Success Response (200)**:
```json
{
  "assigned_shifts": {
    "s1": ["v1", "v2", "v3", "v4"]
  },
  "unfilled_shifts": []
}
```

**Error Response (422)** - When scheduling is impossible/incomplete:
```json
{
  "detail": {
    "error": "Unable to fill all shifts",
    "unfilled_shifts": [
      ["s1", "Delegates", 1],
      ["s1", "Adults", 1]
    ],
    "assigned_shifts": {
      "s1": ["v1", "v2"]
    },
    "volunteers": {
      "v1": {
        "assigned_hours": 2.0,
        "assigned_shifts": ["s1"]
      },
      "v2": {
        "assigned_hours": 2.0,
        "assigned_shifts": ["s1"]
      }
    }
  }
}
```

### 2. Schedule via CSV

**Endpoint**: `POST /schedule/csv`

**Description**: Accepts volunteer and shift data as CSV files and returns assignments as CSV.

**Request**: Multipart form data with two files:
- `volunteers_file`: CSV file with volunteer data
- `shifts_file`: CSV file with shift data

**Volunteers CSV Format**:
```csv
id,name,group,max_hours
v1,John Doe,Delegates,8.0
v2,Jane Smith,Adults,10.0
```

**Shifts CSV Format**:
```csv
id,start,end,required_groups,allowed_groups,excluded_groups
s1,2025-12-01T09:00,2025-12-01T11:00,Delegates:2|Adults:2,Delegates|Adults,
```

**Optional Query Parameter**:
- `strategy`: Optimization strategy (default: `minimize_unfilled`). Valid values: `minimize_unfilled`, `maximize_fairness`, `minimize_overtime`

**Success Response (200)**: CSV data with assignment details
```csv
shift_id,volunteer_id,volunteer_name,start,end,duration_hours
s1,v1,John Doe,2025-12-01T09:00,2025-12-01T11:00,2.00
s1,v2,Jane Smith,2025-12-01T09:00,2025-12-01T11:00,2.00
```

**Error Response (422)** - When scheduling is impossible/incomplete, returns JSON (not CSV):
```json
{
  "detail": {
    "error": "Unable to fill all shifts",
    "unfilled_shifts": [["s1", "Adults", 1]],
    "assigned_shifts": {"s1": ["v1"]},
    "volunteers": {
      "v1": {
        "assigned_hours": 2.0,
        "assigned_shifts": ["s1"]
      }
    }
  }
}
```

## Volunteer Model

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique volunteer identifier |
| `name` | string | Yes | Volunteer's full name |
| `group` | string | No | Volunteer's group/role (e.g., "Delegates", "Adults") |
| `max_hours` | float | No | Maximum hours volunteer can work |

## Shift Model

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique shift identifier |
| `start` | string | Yes | Shift start time (ISO 8601: YYYY-MM-DDTHH:MM) |
| `end` | string | Yes | Shift end time (ISO 8601: YYYY-MM-DDTHH:MM) |
| `required_groups` | object | Yes | Groups needed and quantity (e.g., {"Delegates": 2}) |
| `allowed_groups` | array | No | Restrict shift to specific groups |
| `excluded_groups` | array | No | Groups that cannot work this shift |

## Assignment Algorithm

The scheduler uses a greedy assignment approach:

1. Processes each shift and required group
2. Identifies eligible volunteers (matching group, no conflicts, within hours)
3. Sorts candidates by:
   - Current assigned hours (ascending)
   - Number of assigned shifts (ascending)
   - Maximum hours (descending)
4. Assigns volunteers to shift positions
5. Reports unfilled shift positions

## Example Usage

```bash
# Using curl with JSON (default strategy)
curl -X POST "http://localhost:8000/schedule/json" \
  -H "Content-Type: application/json" \
  -d @schedule_request.json

# Using curl with JSON (maximize fairness)
curl -X POST "http://localhost:8000/schedule/json" \
  -H "Content-Type: application/json" \
  -d '{
    "volunteers": [...],
    "shifts": [...],
    "strategy": "maximize_fairness"
  }'

# Using curl with CSV files (default strategy)
curl -X POST "http://localhost:8000/schedule/csv" \
  -F "volunteers_file=@volunteers.csv" \
  -F "shifts_file=@shifts.csv"

# Using curl with CSV files (minimize overtime)
curl -X POST "http://localhost:8000/schedule/csv?strategy=minimize_overtime" \
  -F "volunteers_file=@volunteers.csv" \
  -F "shifts_file=@shifts.csv"
```

## Error Handling

### HTTP 422 - Unprocessable Entity (Impossible Schedule)

Returned when the scheduler cannot fill all shifts due to insufficient volunteers, conflicts, or capacity constraints. The response includes the partial schedule that was achieved:

```json
{
  "detail": {
    "error": "Unable to fill all shifts",
    "unfilled_shifts": [
      ["shift_id", "group_name", shortage_count]
    ],
    "assigned_shifts": {
      "shift_id": ["volunteer_ids"]
    },
    "volunteers": {
      "volunteer_id": {
        "assigned_hours": 0.0,
        "assigned_shifts": []
      }
    }
  }
}
```

### HTTP 400 - Bad Request (Invalid Input)

Returned for invalid inputs such as malformed data or missing required fields:

```json
{
  "detail": "Error message describing the issue"
}
```

Common causes:
- Invalid date format (must be ISO 8601: YYYY-MM-DDTHH:MM)
- Missing required fields
- Malformed CSV data

## Project Structure

- `scheduler.py`: Core scheduling logic with volunteer and shift classes
- `api_scheduler.py`: FastAPI application and HTTP endpoints

## License

MIT
