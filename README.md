# Volunteer Scheduler API

A FastAPI-based service for automatically assigning volunteers to shifts based on availability, group requirements, and time constraints.

## Features

- **Automatic Shift Assignment**: Intelligently assigns volunteers to shifts while respecting constraints
- **Group-Based Requirements**: Specify required volunteer groups for each shift
- **Time Conflict Detection**: Prevents overlapping shift assignments
- **Capacity Management**: Respects maximum hours per volunteer
- **Flexible Input**: Supports both JSON and CSV input formats
- **Detailed Reporting**: Generates assignment reports and identifies unfilled shifts

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# Install dependencies
pip install fastapi uvicorn pydantic python-multipart

# Navigate to the project directory
cd /Users/arnavshah/Documents/management_simple
```

## Running the Server

```bash
uvicorn api_scheduler:app --reload
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI) is available at `http://localhost:8000/docs`

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

**Response**:
```json
{
  "assigned_shifts": {
    "s1": ["v1", "v2"]
  },
  "unfilled_shifts": [
    ["s1", "Adults", 1]
  ]
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

**Response**: CSV data with assignment details
```csv
shift_id,volunteer_id,volunteer_name,start,end,duration_hours
s1,v1,John Doe,2025-12-01T09:00,2025-12-01T11:00,2.00
```

## Volunteer Model

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique volunteer identifier |
| `name` | string | Yes | Volunteer's full name |
| `group` | string | No | Volunteer's group/role (e.g., "Delegates", "Adults") |
| `max_hours` | float | Yes | Maximum hours volunteer can work |

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

The API returns HTTP 400 errors with details for invalid inputs:

```json
{
  "detail": "Error message describing the issue"
}
```

Common errors:
- Invalid date format (must be ISO 8601: YYYY-MM-DDTHH:MM)
- Missing required fields
- Malformed CSV data

## Project Structure

- `scheduler.py`: Core scheduling logic with volunteer and shift classes
- `api_scheduler.py`: FastAPI application and HTTP endpoints

## License

MIT
