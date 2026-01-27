# 🗓️ Volunteer Scheduler API v2.1 (Go Edition)

A high-performance, developer-first API for intelligent shift scheduling. Re-engineered in **Go** for maximum throughput, stateless authentication, and seamless Vercel integration.

[![Vercel Deployment](https://img.shields.io/badge/Deployed%20on-Vercel-black?style=for-the-badge&logo=vercel)](https://shift-scheduler-api-xi.vercel.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Go Version](https://img.shields.io/badge/Go-1.23-blue?style=for-the-badge&logo=go)](https://go.dev/)

---

## ✨ Features

- **🚀 Go-Powered Performance**: Migrated from Python to Go for sub-millisecond scheduling and concurrent processing.
- **🔒 Stateless HMAC API Keys**: Ultra-secure authentication using cryptographic signatures (HMAC-SHA256).
- **🎨 Embedded Admin UI + Sandbox**: A beautiful dashboard for managing keys and a **"Try it Now"** sandbox for instant API testing.
- **🔬 Conflict Resolution**: Intelligent feedback on why shifts couldn't be filled (AI-style insights).
- **⚖️ Fairness Metrics**: Real-time tracking of workload distribution using Standard Deviation scoring.
- **📊 Precision Tracking**: Detailed usage metrics tracking processed shifts and volunteers.
- **📥 Universal Input**: Native support for JSON and CSV with seamless pre-filling of existing assignments.

---

## 🚀 Quick Access

| Resource | Description | Link |
| :--- | :--- | :--- |
| **Integration Guide** | Step-by-step guide for external developers | [Read Guide](./API_INTEGRATION_GUIDE.md) |
| **Admin Dashboard** | Manage keys, view usage, and **test in the sandbox** | [Open Admin](https://shift-scheduler-api-xi.vercel.app/admin) |
| **Live API** | Health check and version info | [Check API](https://shift-scheduler-api-3nxm.vercel.app/) |


---

## 🛠️ Local Setup

Get the API running locally in under 60 seconds:

```bash
# Clone and enter
git clone https://github.com/greenmartialarts/shift-scheduler-api
cd shift-scheduler-api

# Setup environment (requires PostgreSQL or SQLite)
cp .env.example .env

# Start the server
go run cmd/server/main.go
```

> [!NOTE]
> Static assets are automatically bundled using Go 1.23's `embed` functionality. No external web server is required to serve the Admin UI.

---

## 🔑 Authentication

The API has moved to a **Stateless HMAC** strategy. If you had a legacy API key, you must request or generate a new one.

- **Admin Logic**: The `/admin` route automatically provisions a default account from your `.env` if none exists.
- **API Keys**: All requests must include the HMAC key in the `Authorization` header.

---

## 🧪 Tech Stack

- **Go (Golang) 1.23**: Core language for high-performance server logic.
- **Gin**: Robust web framework for routing and middleware.
- **GORM**: Type-safe ORM for PostgreSQL and SQLite.
- **PostgreSQL**: Production database for API keys and tracking.
- **Vercel**: Serverless deployment for global scalability.
- **Go Embed**: Native asset bundling for zero-dependency deployments.

---

Built with ❤️ by [Arnav Shah](https://github.com/arnav-shah)
MIT License. 2026.
