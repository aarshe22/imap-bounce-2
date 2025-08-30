# webui.py
import os, sqlite3, pandas as pd
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dotenv import load_dotenv
from starlette.status import HTTP_401_UNAUTHORIZED
from io import BytesIO, StringIO

load_dotenv()
DB_PATH = "/data/bounces.db"
ADMIN_PASS = os.getenv("ADMIN_PASS","changeme")

app = FastAPI(title="IMAP Bounce Dashboard")
security = HTTPBasic()

def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.password != ADMIN_PASS:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return True

def query_db(query, params=()):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    con.close()
    return [dict(ix) for ix in rows]

@app.get("/", response_class=HTMLResponse)
def dashboard(auth: bool = Depends(check_auth)):
    return HTMLResponse("<h1>📬 Bounce Dashboard is running</h1>")

@app.get("/api/logs")
def api_logs(auth: bool = Depends(check_auth)):
    return {"data": query_db("SELECT id,date,email,status,reason,domain FROM bounces ORDER BY date DESC LIMIT 500")}

@app.get("/api/retry/{bounce_id}")
def api_retry(bounce_id: int, auth: bool = Depends(check_auth)):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("UPDATE bounces SET status='retry_queued' WHERE id=?", (bounce_id,))
    con.commit()
    con.close()
    return RedirectResponse("/", status_code=302)

@app.get("/export/csv")
def export_csv(auth: bool = Depends(check_auth)):
    df = pd.DataFrame(query_db("SELECT * FROM bounces"))
    s = StringIO()
    df.to_csv(s, index=False)
    return StreamingResponse(
        iter([s.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition":"attachment; filename=bounces.csv"}
    )

@app.get("/export/excel")
def export_excel(auth: bool = Depends(check_auth)):
    df = pd.DataFrame(query_db("SELECT * FROM bounces"))
    o = BytesIO()
    df.to_excel(o, index=False)
    o.seek(0)
    return StreamingResponse(
        o,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment; filename=bounces.xlsx"}
    )