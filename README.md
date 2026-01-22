# 🗓️ Volunteer Scheduler API v2.1 (Go Edition)

A high-performance, developer-first API for intelligent shift scheduling. Re-engineered in **Go** for maximum throughput, stateless authentication, and seamless Vercel integration.

[![Vercel Deployment](https://img.shields.io/badge/Deployed%20on-Vercel-black?style=for-the-badge&logo=vercel)](https://shift-scheduler-api-xi.vercel.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Go Version](https://img.shields.io/badge/Go-1.23-blue?style=for-the-badge&logo=go)](https://go.dev/)

---

## ✨ Features

- **🚀 Ultra-Fast Scheduling**: Optimized Go engine for sub-millisecond scheduling, pre-calculation of shift metrics, and efficient volunteer matching.
- **🔒 Stateless HMAC API Keys**: Secure, high-speed authentication using cryptographic signatures (HMAC-SHA256) with zero-query verification.
- **⚡ Optimized DB Layer**: Efficient single-query upserts for usage tracking, designed specifically for serverless free-tier constraints.
- **🎨 Embedded Admin UI**: A beautiful, lightweight dashboard for managing API keys, bundled via `go:embed`.
- **📥 Universal Input**: Native support for JSON and CSV with seamless pre-filling of existing assignments.

---

## 🚀 Quick Access

| Resource | Description | Link |
| :--- | :--- | :--- |
| **Integration Guide** | Step-by-step guide for external developers | [Read Guide](./API_INTEGRATION_GUIDE.md) |
| **Admin Dashboard** | Manage keys and view usage stats | [Open Admin](https://shift-scheduler-api-xi.vercel.app/admin) |
| **Live API** | Health check and version info | [Check API](https://shift-scheduler-api-xi.vercel.app/) |


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
