import os
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response
from dotenv import load_dotenv
from db import query_bounces, count_bounces, insert_bounce, init_db

# Load environment
load_dotenv()

WEBUI_PASSWORD = os.getenv("WEBUI_PASSWORD", "changeme")
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "supersecret")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Static files (e.g. dashboard.html, CSS, JS)
app.mount("/static", StaticFiles(directory="docs"), name="static")

# Ensure DB is ready
init_db()


# ---------- Helpers ----------
def require_login(request: Request):
    if not request.session.get("authenticated"):
        return False
    return True


# ---------- Routes ----------
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    with open("docs/login.html") as f:
        return HTMLResponse(f.read())


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == WEBUI_PASSWORD:
        request.session["authenticated"] = True
        return RedirectResponse(url="/", status_code=302)
    return HTMLResponse("<h3>Invalid password</h3>", status_code=401)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not require_login(request):
        return RedirectResponse(url="/login", status_code=302)
    with open("docs/dashboard.html") as f:
        return HTMLResponse(f.read())


@app.get("/api/logs")
async def api_logs(
    request: Request,
    draw: int = 1,
    start: int = 0,
    length: int = 25,
    date_from: str = None,
    date_to: str = None,
    status: str = None,
    domain: str = None,
):
    if not require_login(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "status": status,
        "domain": domain,
    }

    data = query_bounces(filters, limit=length, offset=start)
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
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    conn_data = []
    from db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT domain, COUNT(*) as count FROM bounces GROUP BY domain ORDER BY count DESC LIMIT 5")
    rows = cur.fetchall()
    conn.close()

    for row in rows:
        conn_data.append({"domain": row["domain"], "count": row["count"]})

    return conn_data