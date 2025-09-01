import os
import sqlite3
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from db import fetch_bounces, count_bounces

# Load environment variables from data/.env
load_dotenv(dotenv_path="data/.env")

WEBUI_PASSWORD = os.getenv("WEBUI_PASSWORD")
SESSION_SECRET = os.getenv("SESSION_SECRET")

if not WEBUI_PASSWORD or not SESSION_SECRET:
    raise RuntimeError("WEBUI_PASSWORD and SESSION_SECRET must be set in data/.env")

app = FastAPI()

# Middleware for session handling
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# Mount docs/ as static so CSS/JS can load
app.mount("/static", StaticFiles(directory="docs"), name="static")


def require_login(request: Request) -> bool:
    return bool(request.session.get("authenticated"))


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    try:
        with open(os.path.join("docs", "login.html")) as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Login page missing</h1>", status_code=500)


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if password == WEBUI_PASSWORD:
        request.session["authenticated"] = True
        return RedirectResponse("/", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    try:
        with open(os.path.join("docs", "index.html")) as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Dashboard page missing</h1>", status_code=500)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


# -----------------------------
# API ENDPOINTS
# -----------------------------

@app.get("/api/logs")
async def api_logs(request: Request,
                   draw: int = 1,
                   start: int = 0,
                   length: int = 25,
                   date_from: str = "",
                   date_to: str = "",
                   status: str = "",
                   domain: str = ""):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    filters = {"date_from": date_from, "date_to": date_to,
               "status": status, "domain": domain}
    data = fetch_bounces(start, length, filters)
    total = count_bounces(filters)

    return {
        "draw": draw,
        "recordsTotal": total,
        "recordsFiltered": total,
        "data": data,
    }


@app.get("/api/domain_stats")
async def api_domain_stats(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    conn = sqlite3.connect("data/bounces.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT domain, COUNT(*) as count FROM bounces GROUP BY domain ORDER BY count DESC LIMIT 5")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return JSONResponse(rows)


@app.get("/api/retry/{bounce_id}")
async def retry_bounce(bounce_id: int, request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    # Placeholder: retry logic (send original message again)
    # For now just return JSON
    return {"status": "ok", "message": f"Retry queued for bounce ID {bounce_id}"}