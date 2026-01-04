# Scheduler API Integration Guide

Welcome to the **Volunteer Scheduler API**! This guide will help you integrate our powerful, randomized greedy scheduler into your own website or application.

## 1. Requesting an API Key
To get started, you will need a unique API Key. Please email your request to:
📧 **arnav.shah.2k10@gmail.com**

Include your website URL and estimated daily scheduling volume.

---

## 2. Authentication
All API requests must include your API key in the `Authorization` header as a Bearer token:

```http
Authorization: Bearer YOUR_API_KEY
```

---

## 3. The Core Scheduling Endpoint
The primary endpoint for scheduling is `POST /schedule/json`.

### Request Schema (JSON)
| Field | Type | Description |
| :--- | :--- | :--- |
| `volunteers` | `Array` | List of available workers (id, name, group, max_hours). |
| `unassigned_shifts` | `Array` | Shifts that need filling (id, start, end, required_groups). |
| `current_assignments` | `Array` | (Optional) Existing assignments to lock in. |

#### Example Request Body
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
const API_URL = "https://your-scheduler-instance.vercel.app/schedule/json";
const API_KEY = "YOUR_API_KEY_HERE";

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
    console.error("Scheduling failed:", error.detail);
    return null;
  }

  const result = await response.json();
  console.log("Assignments:", result.assigned_shifts);
  console.log("Gaps:", result.unfilled_shifts);
  return result;
}
```

---

## 5. Full Example Interaction

### Request (cURL)
```bash
curl -X POST https://your-scheduler.vercel.app/schedule/json \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "volunteers": [
      { "id": "v1", "name": "Alice", "group": "Delegates", "max_hours": 40 },
      { "id": "v2", "name": "Bob", "group": "Security", "max_hours": 40 }
    ],
    "unassigned_shifts": [
      {
        "id": "s1",
        "start": "2026-05-01T09:00:00Z",
        "end": "2026-05-01T12:00:00Z",
        "required_groups": { "Delegates": 1 }
      },
      {
        "id": "s2",
        "start": "2026-05-01T13:00:00Z",
        "end": "2026-05-01T15:00:00Z",
        "required_groups": { "Security": 1 }
      }
    ],
    "current_assignments": [
      { "shift_id": "s1", "volunteer_id": "v1" }
    ]
  }'
```

### Response (JSON)
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
- **Randomized Greedy Logic**: Every request creates a different valid schedule, ensuring fairness over time.
- **Pre-filling**: Lock in existing assignments and the API will work around them.
- **"Best Effort" Handling**: If a shift can't be filled, the API returns the partial schedule and details the gaps in `unfilled_shifts`.
- **Usage Tracking**: You can see your total processed shifts and volunteers in our Admin Dashboard.

---

## 7. Support
If you encounter any issues or have feature requests, please contact us at:
📧 **arnav.shah.2k10@gmail.com**
