# Volunteer Scheduler API

A FastAPI-based service for automatically assigning volunteers to shifts based on availability, group requirements, and time constraints.

## Features

- **Automatic Shift Assignment**: Intelligently assigns volunteers to shifts while respecting constraints
- **Group-Based Requirements**: Specify required volunteer groups for each shift
- **Time Conflict Detection**: Prevents overlapping shift assignments
- **Capacity Management**: Respects maximum hours per volunteer
- **Flexible Input**: Supports both JSON and CSV input formats
- **Detailed Reporting**: Generates assignment reports and identifies unfilled shifts

## Try the API Here :
https://shift-scheduler-api-j4wh.onrender.com

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# Navigate to the project directory
cd management_simple

# Install dependencies
pip install -r requirements.txt
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

### Deploying to Netlify

A `netlify.toml` file is included that automatically:
1. Installs dependencies from `requirements.txt`
2. Starts the uvicorn server

Just push to your repository and Netlify will build and deploy automatically.

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
  ]
}
```

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
# Using curl with JSON
curl -X POST "http://localhost:8000/schedule/json" \
  -H "Content-Type: application/json" \
  -d @schedule_request.json

# Using curl with CSV files
curl -X POST "http://localhost:8000/schedule/csv" \
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
