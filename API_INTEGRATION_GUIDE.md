# Scheduler API Integration Guide v2

Welcome to the **Volunteer Scheduler API**! This guide will help you integrate our high-performance Go scheduler into your own website or application.

## 1. Requesting an API Key
To get started, you will need a unique **HMAC-signed API Key**. Please email your request to:
📧 **arnav.shah.2k10@gmail.com**

> [!IMPORTANT]
> Version 2.0 uses a new stateless authentication strategy. Legacy API keys from v1.0 (Python) will no longer work.

---

## 2. Authentication
All API requests must include your API key in the `Authorization` header:

```http
Authorization: Bearer userID.signature
```

---

## 3. Core Endpoints

### JSON Scheduling
- **Endpoint**: `POST /schedule/json` (or `/api/schedule`)
- **Body**: Standard JSON input

### CSV Scheduling
- **Endpoint**: `POST /schedule/csv`
- **Body**: `multipart/form-data` with files `volunteers_file`, `shifts_file`, and optional `assignments_file`.

### JSON Request Schema
| Field | Type | Description |
| :--- | :--- | :--- |
| `volunteers` | `Array` | List of available workers (id, name, group, max_hours). |
| `unassigned_shifts` | `Array` | Shifts that need filling (id, start, end, required_groups). |
| `current_assignments` | `Array` | (Optional) Existing assignments to lock in. |

#### Example JSON Body
```json
{
  "volunteers": [
    { "id": "v1", "name": "Alice", "group": "Delegates", "max_hours": 20 }
  ],
  "unassigned_shifts": [
    {
      "id": "s1",
      "start": "2026-05-01T09:00:00Z",
      "end": "2026-05-01T17:00:00Z",
      "required_groups": { "Delegates": 1 }
    }
  ],
  "current_assignments": []
}
```

---

## 4. Implementation Example (JavaScript)

```javascript
const API_URL = "https://shift-scheduler-api-xi.vercel.app/schedule/json";
const API_KEY = "your_user_id.your_hmac_signature";

async function generateSchedule(data) {
  const response = await fetch(API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${API_KEY}`
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const error = await response.json();
    console.error("Scheduling failed:", error);
    return null;
  }

  const result = await response.json();
  console.log("Assignments:", result.assigned_shifts);
  return result;
}
```

---

## 5. Response Format (JSON Parity)

The response maintains full backward compatibility with the v1.0 format:

```json
{
  "assigned_shifts": {
    "s1": ["v1"],
    "s2": ["v2"]
  },
  "unfilled_shifts": [],
  "volunteers": {
    "v1": { "assigned_hours": 3.0, "assigned_shifts": ["s1"] },
    "v2": { "assigned_hours": 2.0, "assigned_shifts": ["s2"] }
  }
}
```

---

## 6. Key Features
- **Stateless Verification**: Blazing fast authentication that doesn't wait for a database query.
- **Randomized Fairness**: Every request creates a different valid schedule to prevent scheduling bias.
- **Pre-filling**: Lock in existing assignments and the API will work around them.
- **CSV Support**: Bulk process schedules by uploading files directly to the API.

---

## 7. Support
If you encounter any issues or have feature requests, please contact us at:
📧 **arnav.shah.2k10@gmail.com**
