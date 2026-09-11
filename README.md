# 🚀 API Health & Reliability Monitor

> A lightweight web dashboard for monitoring API availability, response time, and reliability.

The **API Health & Reliability Monitor** is a Flask-based web application that allows users to register APIs, perform real-time health checks, track monitoring history, and view reliability analytics through a clean dashboard.

---

## ✨ Features

- 🔗 **API Registration** — Add and manage API endpoints
- ❤️ **Health Monitoring** — Check whether an API is UP or DOWN
- ⚡ **Response Time Tracking** — Measure API response time in milliseconds
- 📊 **Reliability Analytics** — View availability and monitoring statistics
- 📝 **Monitoring History** — Keep a record of previous health checks
- 🔄 **Check All APIs** — Monitor all registered APIs at once
- 🗑️ **API Management** — Delete registered APIs
- 🚫 **Duplicate Prevention** — Prevent duplicate API URLs
- 📱 **Responsive UI** — Clean dashboard that works across screen sizes

---

## 🖥️ Dashboard

The dashboard provides an overview of:

| Metric | Description |
|---|---|
| Total APIs | Number of registered APIs |
| Healthy APIs | APIs currently responding successfully |
| Down APIs | APIs that are unavailable or returning errors |
| Not Checked | APIs that have not been monitored yet |

Each registered API provides quick actions for:

**Check · History · Analytics · Delete**

---

## 🛠️ Tech Stack

**Backend**
- Python
- Flask

**Frontend**
- HTML5
- CSS3

**Database**
- SQLite

**Libraries**
- Requests

**Deployment**
- Gunicorn

**Development Tools**
- Git
- GitHub

---

## ⚙️ How It Works

```text
              Register API
                   │
                   ▼
          Store API in SQLite
                   │
                   ▼
            Health Check
                   │
          ┌────────┴────────┐
          ▼                 ▼
     HTTP Response      Request Error
          │                 │
          ▼                 ▼
      UP / DOWN           DOWN
          │
          ▼
   Store Monitoring Data
          │
     ┌────┴─────┐
     ▼          ▼
  History    Analytics
