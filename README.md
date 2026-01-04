# 🗓️ Volunteer Scheduler API v2.0

A high-performance, developer-first API for intelligent shift scheduling. Built for speed, fairness, and seamless integration.

[![Vercel Deployment](https://img.shields.io/badge/Deployed%20on-Vercel-black?style=for-the-badge&logo=vercel)](https://shift-scheduler-api-xi.vercel.app/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

---

## ✨ Features

- **🚀 Near-Instant Scheduling**: Advanced randomized greedy logic handles thousands of slots in milliseconds.
- **🎨 Modern Admin UI**: Beautiful, glassmorphic dashboard for managing API keys and monitoring usage.
- **📊 Precision Tracking**: Track not just requests, but actual volume (total shifts and volunteers processed).
- **🔒 Multi-Auth Security**: Supports full JWT admin sessions and a stateless `ADMIN_MASTER_KEY` for automation.
- **🎲 Randomized Fairness**: Every run produces a unique, valid schedule to prevent scheduling bias.
- **📥 Universal Input**: Native support for JSON and CSV with seamless pre-filling of existing assignments.

---

## 🚀 Quick Access

| Resource | Description | Link |
| :--- | :--- | :--- |
| **Live API Docs** | Interactive Swagger/OpenAPI documentation | [View Docs](https://shift-scheduler-api-xi.vercel.app/docs) |
| **Integration Guide** | Step-by-step guide for external developers | [Read Guide](./API_INTEGRATION_GUIDE.md) |
| **Admin Dashboard** | Manage keys and view usage stats | [Open Admin](https://shift-scheduler-api-xi.vercel.app/admin) |


---

## 🛠️ Local Setup

Get the API running locally in under 60 seconds:

```bash
# Clone and enter
git clone https://github.com/greenmartialarts/shift-scheduler-api
cd shift-scheduler-api

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn api_scheduler:app --reload
```

> [!TIP]
> Use our `setup_admin.py` script to quickly provision your first administrative account for the dashboard.

---

## 🔑 Requesting Access

The API uses **API Key Authentication**. If you are a developer looking to integrate this into your project, please contact the administrator:

📧 **arnav.shah.2k10@gmail.com**

---

## 🧪 Tech Stack

- **FastAPI**: Blazing fast, asynchronous Python web framework.
- **PostgreSQL/SQLite**: Dual-engine support for local development and production persistence.
- **Supabase**: Powering our production-grade persistent data store.
- **Pydantic**: Robust data validation and serialization.

---

Built with ❤️ by [Arnav Shah](https://github.com/arnav-shah)
MIT License. 2026.
