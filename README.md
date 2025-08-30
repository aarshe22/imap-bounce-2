# 📬 IMAP Bounce Processor & Dashboard

A production-ready Dockerized application that:

- Monitors an **IMAP inbox** for bounced emails  
- Extracts failed recipient addresses, original TO/CC, and reasons (RFC 3463 / SMTP codes)  
- Sends **notification emails** to support teams  
- Stores results in **SQLite**  
- Provides a modern **web dashboard** for search, filtering, retry, export, and analytics  
- Sends a **daily summary email** with category + domain breakdowns  
- Retries failed notifications up to 3 times, then quarantines them  

---

## 🚀 Features

- **IMAP Workflow**
  - New → `INBOX`
  - Success → `PROCESSED`
  - Failed → `PROBLEM`
  - Non-bounces → `SKIPPED`
  - **Test Mode** → `TEST`, `TESTPROCESSED`, `TESTPROBLEM`, `TESTSKIPPED`

- **Bounce Intelligence**
  - Full RFC 3463 enhanced SMTP code dictionary
  - Legacy 3-digit SMTP codes
  - Provider-specific rules (Gmail, Outlook, Yahoo, iCloud)
  - Categories: Invalid User, Mailbox Full, Spam/Blocked, Transient Failure

- **Dashboard**
  - Filters: date range, domain, status
  - Retry button (requeue bounce immediately)
  - CSV / Excel export
  - Domain health → Top 5 domains (Chart.js pie chart)
  - Daily bounce trend (line chart)
  - Dark mode toggle
  - Responsive Bootstrap 5 UI

- **Reports**
  - Daily summary email
  - Includes totals, categories, top 5 domains, detailed log

- **Resilience**
  - Auto-detects stuck IMAP sessions and reconnects
  - Retry queue with exponential backoff
  - Logs persisted under `/data`

---

## 📦 Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/aarshe22/imap-bounce-app.git
cd imap-bounce-app
cp data/.env.example data/.env
```

Fill out `data/.env` with your real credentials.

---

### 2. Run with Docker Compose

```bash
docker-compose up -d
```

- Processor runs every 5 minutes  
- Retry queue every 15 minutes  
- Daily summary at midnight UTC  

---

## 🔑 Access

- **Dashboard**:  
  `https://<server-ip>:8888/`  
  (accept self-signed cert, or use real certs via `.env`)  

- **Login**:  
  Any username, password = `ADMIN_PASS` in `.env`  

---

## 🛡 Security

- HTTPS enforced (self-signed by default)  
- HTTP → HTTPS redirect  
- BasicAuth (`ADMIN_PASS`)  
- HSTS headers enabled  
- No secrets in repo (`.env` in `.gitignore`)  

---

## 🗂 Project Structure

```
imap-bounce-app/
├── app/
│   ├── bounce_rules.py
│   ├── db.py
│   ├── process_bounces.py
│   ├── retry_queue.py
│   ├── daily_summary.py
│   ├── webui.py
│   └── requirements.txt
├── data/
│   └── .env.example
├── Dockerfile
├── supervisord.conf
├── docker-compose.yml
├── Makefile
├── README.md
└── .gitignore
```

---

## 📊 Screenshots

*(Add dashboard screenshots after first run — charts and filters will show up once data is logged.)*

---

## 🛠 TODO / Future

- Multi-mailbox support  
- Slack/Teams webhook alerts  
- Config-check utility to validate IMAP/SMTP before deploy  
