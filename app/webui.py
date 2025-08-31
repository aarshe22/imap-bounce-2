# webui.py
import os, sqlite3, pandas as pd
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from io import BytesIO, StringIO
from db import fetch_bounces, count_bounces

load_dotenv()
DB_PATH = "/data/bounces.db"
ADMIN_PASS = os.getenv("ADMIN_PASS", "changeme")
SESSION_SECRET = os.getenv("SESSION_SECRET", "supersecretkey")

app = FastAPI(title="IMAP Bounce Dashboard")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# ---------------------------
# Helpers
# ---------------------------
def query_db(query, params=()):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    con.close()
    return [dict(ix) for ix in rows]

def check_session(request: Request):
    return request.session.get("authenticated", False)

def get_flash(request: Request):
    msg = request.session.pop("flash", None)
    return msg

def set_flash(request: Request, message: str):
    request.session["flash"] = message

# ---------------------------
# Dashboard
# ---------------------------
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if not check_session(request):
        return RedirectResponse("/login", status_code=302)

    flash = get_flash(request) or ""
    flash_html = f'<div class="alert alert-info">{flash}</div>' if flash else ""

    # Build page with flash injected separately
    html = f"""
    <html><head>
    <title>IMAP Bounce Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head><body>
    <div class="container py-4">
    {flash_html}
    <h1>📬 Bounce Dashboard</h1>
    <a href="/logout" class="btn btn-danger btn-sm float-end">Logout</a>
    """

    # Append static HTML/JS that uses { } freely
    html += """
    <!-- Filters -->
    <div class="row mb-3">
      <div class="col-md-3">
        <label>Date From</label>
        <input type="date" id="dateFrom" class="form-control">
      </div>
      <div class="col-md-3">
        <label>Date To</label>
        <input type="date" id="dateTo" class="form-control">
      </div>
      <div class="col-md-3">
        <label>Status</label>
        <select id="statusFilter" class="form-select">
          <option value="">All</option>
          <option>Processed</option>
          <option>Skipped</option>
          <option>Problem</option>
          <option>retry_queued</option>
        </select>
      </div>
      <div class="col-md-3">
        <label>Domain</label>
        <input type="text" id="domainFilter" placeholder="example.com" class="form-control">
      </div>
    </div>

    <div class="mb-3">
      <a href="#" id="exportCsv" class="btn btn-outline-secondary btn-sm">Export CSV</a>
      <a href="#" id="exportExcel" class="btn btn-outline-secondary btn-sm">Export Excel</a>
    </div>

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
        var table = $('#bounces').DataTable({
          serverSide: true,
          processing: true,
          ajax: {
            url: '/api/logs',
            type: 'GET',
            data: function(d) {
              d.date_from = $('#dateFrom').val();
              d.date_to   = $('#dateTo').val();
              d.status    = $('#statusFilter').val();
              d.domain    = $('#domainFilter').val();
            },
            dataSrc: 'data'
          },
          columns: [
            { data: 'id' },
            { data: 'date' },
            { data: 'email_to' },
            { data: 'email_cc' },
            { data: 'status' },
            { data: 'reason' },
            { data: 'domain' },
            { data: 'id', render: function(d){
                return '<a href="/api/retry/'+d+'" class="btn btn-sm btn-primary">Retry</a>';
              }
            }
          ],
          pageLength: 25,
          lengthMenu: [10, 25, 50, 100]
        });

        // Reload when filters change
        $('#dateFrom,#dateTo,#statusFilter,#domainFilter').on('change keyup', function() {
          table.ajax.reload();
        });

        // Export buttons
        $('#exportCsv').click(function(e){
          e.preventDefault();
          var params = $.param({
            date_from: $('#dateFrom').val(),
            date_to: $('#dateTo').val(),
            status: $('#statusFilter').val(),
            domain: $('#domainFilter').val()
          });
          window.location = '/export/csv?' + params;
        });
        $('#exportExcel').click(function(e){
          e.preventDefault();
          var params = $.param({
            date_from: $('#dateFrom').val(),
            date_to: $('#dateTo').val(),
            status: $('#statusFilter').val(),
            domain: $('#domainFilter').val()
          });
          window.location = '/export/excel?' + params;
        });

        // Chart
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

# ---------------------------
# Login/Logout
# ---------------------------
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    flash = get_flash(request) or ""
    flash_html = f'<div class="alert alert-danger">{flash}</div>' if flash else ""
    return HTMLResponse(f"""
    <html><head><title>Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head><body class="container py-5">
    {flash_html}
    <h2>Login</h2>
    <form method="post" action="/login">
      <div class="mb-3"><input type="password" name="password" placeholder="Password" class="form-control" required></div>
      <button type="submit" class="btn btn-primary">Login</button>
    </form>
    </body></html>
    """)

@app.post("/login")
def login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASS:
        request.session["authenticated"] = True
        set_flash(request, "Welcome! You are now logged in.")
        return RedirectResponse("/", status_code=302)
    else:
        set_flash(request, "Invalid password, please try again.")
        return RedirectResponse("/login", status_code=302)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)

# ---------------------------
# API
# ---------------------------
@app.get("/api/logs")
def api_logs(request: Request,
             draw: int = 1,
             start: int = 0,
             length: int = 25,
             date_from: str = None,
             date_to: str = None,
             status: str = None,
             domain: str = None):
    if not check_session(request):
        return RedirectResponse("/login", status_code=302)

    filters = {"date_from": date_from, "date_to": date_to, "status": status, "domain": domain}
    total = count_bounces(filters)
    rows = fetch_bounces(limit=length, offset=start, filters=filters)

    return {
        "draw": draw,
        "recordsTotal": total,
        "recordsFiltered": total,
        "data": rows
    }

@app.get("/api/domain_stats")
def api_domain_stats(request: Request):
    if not check_session(request):
        return RedirectResponse("/login", status_code=302)
    rows = query_db("SELECT domain, COUNT(*) as count FROM bounces GROUP BY domain ORDER BY count DESC LIMIT 5")
    return {"labels": [r["domain"] for r in rows], "counts": [r["count"] for r in rows]}

@app.get("/api/retry/{bounce_id}")
def api_retry(request: Request, bounce_id: int):
    if not check_session(request):
        return RedirectResponse("/login", status_code=302)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("UPDATE bounces SET status='retry_queued' WHERE id=?", (bounce_id,))
    con.commit()
    con.close()
    set_flash(request, f"Bounce ID {bounce_id} queued for retry.")
    return RedirectResponse("/", status_code=302)

# ---------------------------
# Exports
# ---------------------------
@app.get("/export/csv")
def export_csv(request: Request,
               date_from: str = None,
               date_to: str = None,
               status: str = None,
               domain: str = None):
    if not check_session(request):
        return RedirectResponse("/login", status_code=302)

    filters = {"date_from": date_from, "date_to": date_to, "status": status, "domain": domain}
    rows = fetch_bounces(limit=1000000, offset=0, filters=filters)
    df = pd.DataFrame(rows)
    s = StringIO()
    df.to_csv(s, index=False)
    return StreamingResponse(
        iter([s.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition":"attachment; filename=bounces.csv"}
    )

@app.get("/export/excel")
def export_excel(request: Request,
                 date_from: str = None,
                 date_to: str = None,
                 status: str = None,
                 domain: str = None):
    if not check_session(request):
        return RedirectResponse("/login", status_code=302)

    filters = {"date_from": date_from, "date_to": date_to, "status": status, "domain": domain}
    rows = fetch_bounces(limit=1000000, offset=0, filters=filters)
    df = pd.DataFrame(rows)
    o = BytesIO()
    df.to_excel(o, index=False)
    o.seek(0)
    return StreamingResponse(
        o,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment; filename=bounces.xlsx"}
    )