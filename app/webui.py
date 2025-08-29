from fastapi import FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3, os, base64
from collections import Counter
DB_PATH="/data/bounces.db"; ADMIN_PASS=os.getenv("ADMIN_PASS","changeme"); WEBUI_HTTPS_PORT=os.getenv("WEBUI_HTTPS_PORT","8888")
HSTS_MAX_AGE=int(os.getenv("HSTS_MAX_AGE","15552000")); HSTS_INCLUDE_SUBDOMAINS=os.getenv("HSTS_INCLUDE_SUBDOMAINS","true").lower()=="true"
app=FastAPI()
@app.middleware("http")
async def enforce_https_and_hsts(request:Request,call_next):
    proto=request.headers.get("x-forwarded-proto") or request.url.scheme
    if proto!="https":
        host=request.headers.get("host",f"localhost:{WEBUI_HTTPS_PORT}").split(":")[0]
        return RedirectResponse(url=f"https://{host}:{WEBUI_HTTPS_PORT}{request.url.path}",status_code=301)
    response=await call_next(request)
    hsts=f"max-age={HSTS_MAX_AGE}"; 
    if HSTS_INCLUDE_SUBDOMAINS: hsts+="; includeSubDomains"
    response.headers["Strict-Transport-Security"]=hsts; return response
@app.middleware("http")
async def basic_auth(request:Request,call_next):
    auth=request.headers.get("Authorization")
    if not auth or not auth.startswith("Basic "): return Response(headers={"WWW-Authenticate":"Basic"},status_code=status.HTTP_401_UNAUTHORIZED)
    try: decoded=base64.b64decode(auth.split(" ")[1]).decode("utf-8"); _,password=decoded.split(":",1)
    except Exception: return Response(status_code=status.HTTP_400_BAD_REQUEST)
    if password!=ADMIN_PASS: return Response(headers={"WWW-Authenticate":"Basic"},status_code=status.HTTP_401_UNAUTHORIZED)
    return await call_next(request)
def fetch_bounces():
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    rows=c.execute("SELECT timestamp,subject,bounced_email,reason,status FROM bounces ORDER BY timestamp DESC LIMIT 500").fetchall()
    conn.close(); return rows
def fetch_domain_trends():
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    rows=c.execute("SELECT bounced_email,timestamp FROM bounces").fetchall(); conn.close()
    domains=[r[0].split("@")[-1] for r in rows if r[0]]; from collections import Counter; domain_counts=Counter(domains); daily_counts={}
    for _,ts in rows: day=ts.split("T")[0]; daily_counts[day]=daily_counts.get(day,0)+1
    return domain_counts,daily_counts
@app.get("/",response_class=HTMLResponse)
def index():
    rows=fetch_bounces(); domain_counts,daily_counts=fetch_domain_trends()
    html="""<!DOCTYPE html><html><head><title>Bounce Dashboard</title>
    <link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css'>
    <link rel='stylesheet' href='https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css'>
    <script src='https://cdn.jsdelivr.net/npm/chart.js'></script><script src='https://code.jquery.com/jquery-3.6.0.min.js'></script>
    <script src='https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js'></script>
    <script src='https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js'></script></head>
    <body class='container mt-4'><h1>Email Bounce Dashboard</h1><hr>
    <div class='row'><div class='col-md-6'><h3>Bounces by Domain</h3><canvas id='domainChart'></canvas></div>
    <div class='col-md-6'><h3>Daily Bounce Trend</h3><canvas id='dailyChart'></canvas></div></div><hr>
    <h3>Recent Bounces</h3><table id='bouncesTable' class='table table-striped'>
    <thead><tr><th>Time</th><th>Subject</th><th>Bounced Email</th><th>Reason</th><th>Status</th></tr></thead><tbody>"""
    for ts,subject,bounced,reason,status in rows: html+=f"<tr><td>{ts}</td><td>{subject}</td><td>{bounced}</td><td>{reason}</td><td>{status}</td></tr>"
    html+="""</tbody></table><script>$(document).ready(function(){$('#bouncesTable').DataTable();});
    new Chart(document.getElementById('domainChart'),{type:'bar',data:{labels:%s,datasets:[{label:'Bounces per Domain',data:%s,backgroundColor:%s}]} });
    new Chart(document.getElementById('dailyChart'),{type:'line',data:{labels:%s,datasets:[{label:'Daily Bounces',data:%s,backgroundColor:'rgba(54,162,235,0.7)'}]} });
    </script></body></html>"""%(list(domain_counts.keys()),list(domain_counts.values()),
       [f"rgba({(i*50)%255},{(i*80)%255},{(i*110)%255},0.7)" for i in range(len(domain_counts))],
       list(daily_counts.keys()),list(daily_counts.values()))
    return html
