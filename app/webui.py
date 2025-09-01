import os
import sqlite3
import pandas as pd
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.sessions import SessionMiddleware
from starlette.middleware.sessions import SessionMiddleware as StarletteSessionMiddleware
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER
from db import fetch_bounces, count_bounces, log_bounce, init_db

app = FastAPI()

# Session middleware (use starlette)
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret")
app.add_middleware(StarletteSessionMiddleware, secret_key=SECRET_KEY)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


def get_db_connection():
    conn = sqlite3.connect("data/bounces.db")
    conn.row_factory = sqlite3.Row
    return conn


def query_db(query, params=()):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return HTMLResponse("""
    <html>
    <head><title>Login</title></head>
    <body>
    <h2>Login</h2>
    <form action="/login" method="post">
      <input type="password" name="password" placeholder="Password"/>
      <input type="submit" value="Login"/>
    </form>
    </body>
    </html>
    """)


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    correct_password = os.getenv("WEBUI_PASSWORD", "changeme")
    if password == correct_password:
        request.session["authenticated"] = True
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    return HTMLResponse("<h3>Invalid password</h3><a href='/login'>Try again</a>", status_code=401)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/static") or request.url.path.startswith("/login"):
        return await call_next(request)
    if not request.session.get("authenticated"):
        return RedirectResponse("/login")
    return await call_next(request)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    with open("app/templates/dashboard.html") as f:
        return HTMLResponse(f.read())


@app.get("/api/logs")
async def api_logs(
    request: Request,
    draw: int = 1,
    start: int = 0,
    length: int = 25,
    date_from: str = "",
    date_to: str = "",
    status: str = "",
    domain: str = ""
):
    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "status": status,
        "domain": domain
    }
    total = count_bounces(filters)
    rows = fetch_bounces(start=start, length=length, filters=filters)
    data = [dict(r) for r in rows]
    return {
        "draw": draw,
        "recordsTotal": total,
        "recordsFiltered": total,
        "data": data
    }


@app.get("/api/domain_stats")
async def api_domain_stats():
    rows = query_db("SELECT domain, COUNT(*) as count FROM bounces GROUP BY domain ORDER BY count DESC LIMIT 5")
    return [{"domain": r["domain"], "count": r["count"]} for r in rows]