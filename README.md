# 📬 IMAP Bounce Processor & Dashboard

A Dockerized application that:

- Monitors an **IMAP inbox** for **bounced emails**
- Extracts failed recipient addresses + reasons
- Sends **notification emails** about invalid recipients
- Stores all events in a **SQLite database**
- Provides a secure **web dashboard** with search + analytics (Bootstrap + DataTables + Chart.js)
- Sends a **daily summary email**
- Retries failed notifications up to **3 times**, then quarantines them

---

## 🚀 Features

- **IMAP processing (every 5 min)**
  - Parse DSN (RFC 3464) and common bounce formats
  - Detect non-bounce messages (auto-replies, etc.)
  - Move messages into folders:
    - ✅ `PROCESSED` → valid bounce handled
    - ⚠️ `PROBLEM` → retries failed or processing error
    - ↩️ `SKIPPED` → not a bounce

- **Notifications**
  - Email alerts to `NOTIFY_CC` address
  - Retry queue with exponential attempts

- **Analytics**
  - Interactive web dashboard:
    - 🔍 Searchable + sortable table of bounces
    - 📊 Bounce trends by domain (Chart.js)
    - 📈 Daily bounce volume trend
  - Secure:
    - HTTPS enforced (self-signed or real certs)
    - HTTP → HTTPS redirect
    - BasicAuth (`ADMIN_PASS` in `.env`)
    - HSTS enabled

- **Daily Reports**
  - Summarized list of all bounces emailed daily

---

## 📦 Quick Start

### 1. Clone & unzip

```bash
git clone https://github.com/YOURUSER/imap-bounce-app.git
cd imap-bounce-app
```

(or unzip the release package)

---

### 2. Configure

Copy example env file:

```bash
cp data/.env.example data/.env
```

Edit `data/.env` with your IMAP + SMTP details:

```ini
IMAP_SERVER=imap.yourmail.com
IMAP_USER=bounce@yourdomain.com
IMAP_PASS=supersecret

SMTP_SERVER=smtp.yourmail.com
SMTP_PORT=587
SMTP_USER=notifications@yourdomain.com
SMTP_PASS=supersecret

NOTIFY_CC=support@yourdomain.com

WEBUI_HTTPS_PORT=8888
ADMIN_PASS=SuperSecret123
```

---

### 3. Run

```bash
docker-compose up -d --build
```

- Bounce processor runs every **5 minutes**
- Retry queue runs every **15 minutes**
- Daily summary runs at **midnight UTC**

---

## 🔑 Access

- **Dashboard**:  
  `https://<server-ip>:8888/`  
  (accept browser warning if using self-signed cert)

- **Login**:  
  Any username, password = `ADMIN_PASS` from `.env`

---

## 🔐 Security Notes

- Default TLS is **self-signed**.  
  For production, mount real certs into `/data/certs/` and set in `.env`:

```ini
SSL_KEY=/data/certs/server.key
SSL_CRT=/data/certs/server.crt
```

- BasicAuth enforced on dashboard.
- HSTS header locks browsers to HTTPS.
- All sensitive credentials kept in `.env` (never commit to Git).

---

## 🗂 Project Structure

```
imap-bounce-app/
├── app/
│   ├── process_bounces.py    # main IMAP processor
│   ├── retry_queue.py        # retries failed notifications
│   ├── daily_summary.py      # daily report email
│   ├── webui.py              # FastAPI web dashboard
│   ├── db.py                 # SQLite schema + logging
│   ├── bounce_rules.py       # bounce pattern dictionary
│   └── requirements.txt
├── data/
│   ├── .env.example
│   └── (persistent db + logs here)
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 📊 Screenshots

*(Add screenshots of dashboard once running)*

---

## 🛠 TODO / Ideas

- Export JSON API for integration with Grafana/SIEM
- Add provider-specific bounce classifiers
- Improve retry backoff strategy
- Multi-user dashboard with per-domain filtering

---
