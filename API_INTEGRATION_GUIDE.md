# Scheduler API Integration Guide v2.1

Welcome to the **Volunteer Scheduler API**! This guide will help you integrate our high-performance Go scheduler into your own website or application.

## 1. Requesting an API Key
To get started, you will need a unique **HMAC-signed API Key**. Please email your request to:
📧 **arnav.shah.2k10@gmail.com**

> [!IMPORTANT]
> Version 2.0+ uses a stateless authentication strategy. Legacy API keys from v1.0 (Python) will no longer work.

---

## 2. Authentication
All API requests must include your API key in the `Authorization` header:

```http
Authorization: Bearer [user_id].[signature]
```

Example: `Authorization: Bearer arnav.sk_7a9b...2f1c`

---

## 3. Core Endpoints

### 🚀 Scheduling
- **JSON**: `POST /api/schedule`
- **CSV**: `POST /api/schedule/csv` (multipart/form-data)

### 🛠️ Developer Tools
- **Validate**: `POST /api/validate` - Check your JSON format without running the engine.
- **Usage**: `GET /api/usage` - Get your current quota and usage history.

---

## 4. Request & Response Schema (JSON)

### Request Body
| Field | Type | Description |
| :--- | :--- | :--- |
| `volunteers` | `Array` | List of workers (`id`, `name`, `group`, `max_hours`). |
| `unassigned_shifts` | `Array` | Shifts needing filling (`id`, `start`, `end`, `required_groups`). |
| `current_assignments` | `Array` | (Optional) Existing assignments to lock in. |

### Response Body
| Field | Type | Description |
| :--- | :--- | :--- |
| `fairness_score` | `Float` | Workload distribution score (0-100%). Higher is better. |
| `conflicts` | `Array` | Detailed reasons for unfilled shifts. |
| `volunteers` | `Object` | Map of `volunteer_id` -> `{assigned_hours, assigned_shifts}` summary. |

---

## 5. Understanding the Fairness Score

The `fairness_score` measures how evenly shifts are distributed among your volunteers.

- **Unit**: **Percentage (%)** (0 - 100%).
- **Interpretation**:
  - `100.0`: **Perfectly Balanced**. Every volunteer is working the exact same number of hours.
  - `Higher is Better`: 100% means zero variation in workload.
  - `Low Score (<50%)`: **Imbalanced**. Some volunteers are significantly over-scheduled while others are under-utilized.

### 💡 Presentation Tips
When displaying this to your users, you can use the raw percentage directly:

| Score | Rating | UI Suggestion |
| :--- | :--- | :--- |
| **> 90%** | 🌟 Excellent | Green Progress Bar / 5 Stars |
| **70% - 90%** | ✅ Good | Blue Progress Bar / 4 Stars |
| **50% - 70%** | ⚠️ Fair | Yellow Progress Bar / 3 Stars |
| **< 50%** | ❗ Imbalanced | Red Progress Bar / 1-2 Stars |

---
### 📝 Example API Response
```json
{
  "assigned_shifts": {
    "shift_101": ["vol_7", "vol_12"],
    "shift_102": ["vol_3"]
  },
  "unfilled_shifts": ["shift_103"],
  "fairness_score": 88.5,
  "conflicts": [
    {
      "shift_id": "shift_103",
      "group": "Lifeguards",
      "reasons": ["Volunteer vol_7 already reached max_hours (40.0)"]
    }
  ],
  "volunteers": {
    "vol_7": {
      "assigned_hours": 40.0,
      "assigned_shifts": ["shift_100", "shift_101"]
    },
    "vol_12": {
      "assigned_hours": 8.0,
      "assigned_shifts": ["shift_101"]
    }
  }
}
```

---

## 5. Implementation Examples

### 📦 JavaScript SDK (Recommended)
You can integrate the SDK in two ways:

#### Option A: NPM (Modern)
Install the package directly into your project:

```bash
# Install via GitHub until published to registry
npm install github:greenmartialarts/shift-scheduler-api#path:packages/scheduler-sdk
```

```javascript
import SchedulerAPI from '@greenmartialarts/scheduler-sdk';

const scheduler = new SchedulerAPI("your_api_key");
```

#### Option B: CDN / Direct Script
Load it directly from the API service:
`<script src="https://shift-scheduler-api-3nxm.vercel.app/static/scripts/scheduler-sdk.js"></script>`

```javascript
const scheduler = new SchedulerAPI("your_api_key");
```

---

### 🚀 Usage Example

### 🐍 Python
```python
import requests

API_URL = "https://shift-scheduler-api-xi.vercel.app/api/schedule"
API_KEY = "your_api_key"

def get_schedule(data):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.post(API_URL, json=data, headers=headers)
    return response.json()
```

### 💻 cURL
```bash
curl -X POST https://shift-scheduler-api-xi.vercel.app/api/schedule \
     -H "Authorization: Bearer YOUR_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "volunteers": [{"id": "v1", "name": "Alice", "max_hours": 20}],
       "unassigned_shifts": [{"id": "s1", "start": "2026-05-01T09:00:00Z", "end": "2026-05-01T17:00:00Z", "required_groups": {"Staff": 1}}]
     }'
```

---

## 6. Troubleshooting
- **401 Unauthorized**: Your HMAC signature is invalid or the key has been revoked.
- **400 Bad Request**: Check `/api/validate` to see exactly where your JSON structure is failing.
- **Rate Limit**: Use `/api/usage` to check if you have exceeded your daily quota.

---

## 7. Support
📧 **arnav.shah.2k10@gmail.com**
