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
    html = """
    <html><head>
    <title>IMAP Bounce Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head><body>
    <div class="container py-4">
    <h1>📬 Bounce Dashboard</h1>
    <table id="bounces" class="table table-striped table-bordered" style="width:100%">
      <thead>
        <tr>
          <th>ID</th>
          <th>Date</th>
          <th>To</th>
          <th>Cc</th>
          <th>Status</th>
          <th>Reason</th>
          <th>Domain</th>
          <th>Action</th>
        </tr>
      </thead>
    </table>
    <h3 class="mt-5">Top 5 Bounce Domains</h3>
    <canvas id="domainChart"></canvas>
    </div>
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
    <script>
      $(document).ready(function() {
        $('#bounces').DataTable({
          ajax: '/api/logs',
          columns: [
            { data: 'id' },
            { data: 'date' },
            { data: 'email_to' },
            { data: 'email_cc' },
            { data: 'status' },
            { data: 'reason' },
            { data: 'domain' },
            { data: 'id', render: function(d){return '<a href="/api/retry/'+d+'" class="btn btn-sm btn-primary">Retry</a>';}}
          ]
        });
        fetch('/api/domain_stats').then(r=>r.json()).then(data=>{
          new Chart(document.getElementById('domainChart'),{
            type:'pie',
            data:{labels:data.labels,datasets:[{data:data.counts,backgroundColor:['#007bff','#dc3545','#28a745','#ffc107','#17a2b8']}]}
          });
        });
      });
    </script>
    </body></html>
    """
    return HTMLResponse(content=html)

@app.get("/api/logs")
def api_logs(auth: bool = Depends(check_auth)):
    rows = query_db("SELECT id,date,email_to,email_cc,status,reason,domain FROM bounces ORDER BY date DESC LIMIT 500")
    return {"data": rows}

@app.get("/api/domain_stats")
def api_domain_stats(auth: bool = Depends(check_auth)):
    rows = query_db("SELECT domain, COUNT(*) as count FROM bounces GROUP BY domain ORDER BY count DESC LIMIT 5")
    return {"labels": [r["domain"] for r in rows], "counts": [r["count"] for r in rows]}

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
    rows = query_db("SELECT * FROM bounces")
    df = pd.DataFrame(rows)
    s = StringIO()
    df.to_csv(s, index=False)
    return StreamingResponse(
        iter([s.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition":"attachment; filename=bounces.csv"}
    )

@app.get("/export/excel")
def export_excel(auth: bool = Depends(check_auth)):
    rows = query_db("SELECT * FROM bounces")
    df = pd.DataFrame(rows)
    o = BytesIO()
    df.to_excel(o, index=False)
    o.seek(0)
    return StreamingResponse(
        o,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment; filename=bounces.xlsx"}
    )