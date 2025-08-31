# 📬 IMAP Bounce Processor & Dashboard

A Dockerized Python application that:
- Monitors an IMAP inbox for bounce messages.
- Extracts original `To:` and `Cc:` addresses.
- Categorizes bounces by SMTP code and provider patterns.
- Sends bounce notifications automatically.
- Logs all activity into an SQLite database (`/data/bounces.db`).
- Provides a **modern web dashboard** (FastAPI + Bootstrap + DataTables + Chart.js).
- Generates **daily summary emails** of bounce statistics.
- Runs cleanly in **Docker**, scheduled with **supercronic**.

---

## 🚀 Features
- **IMAP Monitoring**  
  - Processes new messages every 5 minutes.  
  - Moves processed bounces to `PROCESSED`, non-bounces to `SKIPPED`, failures to `PROBLEM`.  
  - Supports **test mode** with separate folders (`TEST`, `TESTPROCESSED`, etc.).  

- **Bounce Detection**  
  - Provider-specific regex patterns.  
  - Full **SMTP status code dictionary** (RFC 3463/5248).  
  - DSN header support (`Action`, `Status`).  

- **Notifications**  
  - In normal mode: notify `NOTIFY_CC` **+ all Cc recipients**.  
  - In test mode: notify **only `NOTIFY_CC_TEST`**.  
  - Uses SMTP relay (`SMTP_SERVER` + `SMTP_PORT`).  

- **Web Dashboard**  
  - Login with password (`ADMIN_PASS`).  
  - Session-based auth (no more Basic Auth popups).  
  - Search/filter by **date, domain, status**.  
  - Retry bounces via button.  
  - CSV/Excel export (respects filters).  
  - Chart of top 5 domains causing bounces.  

- **Daily Summary**  
  - Runs once per day at midnight UTC.  
  - Summarizes by status and domain.  
  - Emails to `NOTIFY_CC` (or `NOTIFY_CC_TEST` in test mode).  

---

## 🛠 Installation

### 1. Clone Repo
```bash
git clone https://github.com/aarshe22/imap-bounce-2.git
cd imap-bounce-2
```

### 2. Configure Environment
Copy `.env.example` → `.env` and edit values:
```bash
cp data/.env.example data/.env
nano data/.env
```

Key settings:
- `IMAP_SERVER`, `IMAP_PORT`, `IMAP_USER`, `IMAP_PASS`
- `IMAP_FOLDER_*` (normal + test)
- `NOTIFY_CC`, `NOTIFY_CC_TEST`
- `IMAP_TEST_MODE` (`true` or `false`)
- `SMTP_SERVER`, `SMTP_PORT`
- `ADMIN_PASS` (dashboard password)
- `SESSION_SECRET` (random string)

### 3. Start Container
```bash
sudo docker compose up -d
```

### 4. Access Dashboard
Visit:  
👉 `http://<server-ip>:8888` (or port set by `WEBUI_PORT`)  
Login with password from `.env` (`ADMIN_PASS`).  

---

## 📅 Scheduled Jobs

Jobs are defined in `crontab` and executed by **supercronic**:

```cron
# Every 5 minutes: process new messages
*/5 * * * * python /app/process_bounces.py >> /data/cron.out.log 2>> /data/cron.err.log

# Every 30 minutes: retry queued bounces
*/30 * * * * python /app/retry_queue.py >> /data/retry.out.log 2>> /data/retry.err.log

# Daily at midnight UTC: send summary
0 0 * * * python /app/daily_summary.py >> /data/summary.out.log 2>> /data/summary.err.log
```

Logs are persisted under `/data/*.log`.

---

## 📊 Database
SQLite database stored at `/data/bounces.db`:
- `id` → unique row
- `date` → message date
- `email_to` → top-level `To:` address
- `email_cc` → comma-separated `Cc:` list
- `status` → `Processed`, `Skipped`, `Problem`, `retry_queued`
- `reason` → bounce reason (regex, SMTP code, DSN)
- `domain` → extracted domain from `email_to`
- `retries` → retry attempts count

Query DB manually:
```bash
sqlite3 data/bounces.db "SELECT * FROM bounces LIMIT 10;"
```

---

## 📦 Build & Run (Optional Local Build)

### Build Image
```bash
sudo docker build -t imap-bounce-app .
```

### Run
```bash
sudo docker run -d   --name imap-bounce   --env-file ./data/.env   -v $(pwd)/data:/data   -p 8888:8888   imap-bounce-app
```

---

## 🔒 Security
- Runs as non-root `appuser`.  
- Session-based auth for dashboard (`ADMIN_PASS`).  
- Database + logs persisted outside container in `/data`.  
- Test mode (`IMAP_TEST_MODE=true`) prevents accidental notifications to real users.  

---

## 📤 Exports
- CSV export → `/export/csv`
- Excel export → `/export/excel`

Both respect filters (date range, domain, status).

---

## ⚡ Tech Stack
- **Python 3.12**  
- **FastAPI** + **Uvicorn**  
- **SQLite** for persistence  
- **supercronic** for scheduling  
- **Bootstrap 5** + **DataTables** + **Chart.js**  

---

## 👨‍💻 Development Notes
- `process_bounces.py` → main IMAP processor  
- `retry_queue.py` → retries failed bounces  
- `daily_summary.py` → sends daily report  
- `bounce_rules.py` → regex + SMTP code bounce detection  
- `webui.py` → web dashboard  
- `db.py` → database utilities  

---

## 📜 License
MIT License – use freely for personal or commercial projects.

---

## 🤝 Credits
Developed with ❤️ to make bounce handling transparent, reliable, and admin-friendly.
