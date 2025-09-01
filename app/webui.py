import os
import subprocess
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv, set_key
from db import query_bounces, count_bounces

# ============================================
# Load environment and validate
# ============================================
ENV_FILE = "data/.env"
load_dotenv(ENV_FILE)

REQUIRED_VARS = [
    # IMAP
    "IMAP_SERVER", "IMAP_PORT", "IMAP_SECURE",
    "IMAP_USER", "IMAP_PASS",
    "IMAP_FOLDER_INBOX", "IMAP_FOLDER_PROCESSED",
    "IMAP_FOLDER_PROBLEM", "IMAP_FOLDER_SKIPPED",
    "IMAP_FOLDER_TEST", "IMAP_FOLDER_TESTPROCESSED",
    "IMAP_FOLDER_TESTPROBLEM", "IMAP_FOLDER_TESTSKIPPED",
    # SMTP
    "SMTP_SERVER", "SMTP_PORT", "SMTP_USER", "SMTP_PASS",
    # WebUI
    "WEBUI_PORT", "SESSION_SECRET", "ADMIN_PASS"
]

missing_vars = [var for var in REQUIRED_VARS if not os.getenv(var)]

WEBUI_PORT = int(os.getenv("WEBUI_PORT", "8888"))
SESSION_SECRET = os.getenv("SESSION_SECRET", "changeme")
ADMIN_PASS = os.getenv("ADMIN_PASS", "changeme")

# Runtime toggles
TEST_MODE = os.getenv("IMAP_TEST_MODE", "false").lower() == "true"
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"

# ============================================
# FastAPI app setup
# ============================================
app = FastAPI(title="IMAP Bounce Processor")

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# Static + templates
app.mount("/static", StaticFiles(directory="docs/static"), name="static")
templates = Jinja2Templates(directory="docs/templates")

# ============================================
# Routes
# ============================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASS:
        request.session["user"] = "admin"
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid password"})


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login")

    bounce_count = count_bounces({})
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "bounce_count": bounce_count,
        "missing_vars": missing_vars
    })


@app.get("/api/logs", response_class=JSONResponse)
async def api_logs(request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login")

    params = dict(request.query_params)
    rows = query_bounces(params)
    return {"data": rows, "recordsTotal": len(rows), "recordsFiltered": len(rows)}


@app.get("/api/domain_stats", response_class=JSONResponse)
async def api_domain_stats(request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login")

    rows = query_bounces({"group_by": "domain"})
    return {"data": rows}


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

# ============================================
# Manual task execution with live streaming
# ============================================

def stream_process(command: list[str]):
    """Generator to stream stdout/stderr lines from a subprocess in real time"""
    process = subprocess.Popen(
        ["python", "-u"] + command[1:],  # force unbuffered Python
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    try:
        for line in iter(process.stdout.readline, ''):
            # Preserve natural newlines; SSE requires double newline
            yield f"data: {line}\n\n"
    finally:
        process.stdout.close()
        process.wait()
        yield f"data: --- Process finished with exit code {process.returncode} ---\n\n"


@app.get("/run_bounce_check", response_class=HTMLResponse)
async def run_bounce_check_page(request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("task_log.html", {"request": request, "task_name": "Bounce Check", "stream_url": "/run_bounce_check_stream"})


@app.get("/run_bounce_check_stream")
async def run_bounce_check_stream(request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login")
    return StreamingResponse(stream_process(["python", "/app/process_bounces.py"]), media_type="text/event-stream")


@app.get("/run_retry_queue", response_class=HTMLResponse)
async def run_retry_queue_page(request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("task_log.html", {"request": request, "task_name": "Retry Queue", "stream_url": "/run_retry_queue_stream"})


@app.get("/run_retry_queue_stream")
async def run_retry_queue_stream(request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login")
    return StreamingResponse(stream_process(["python", "/app/retry_queue.py"]), media_type="text/event-stream")

# ============================================
# Toggle endpoints
# ============================================

@app.get("/get_toggles", response_class=JSONResponse)
async def get_toggles(request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login")
    return {"test_mode": TEST_MODE, "scheduler": SCHEDULER_ENABLED}


@app.post("/toggle_test_mode", response_class=JSONResponse)
async def toggle_test_mode(request: Request):
    global TEST_MODE
    if "user" not in request.session:
        return RedirectResponse(url="/login")

    TEST_MODE = not TEST_MODE
    set_key(ENV_FILE, "IMAP_TEST_MODE", "true" if TEST_MODE else "false")
    return {"test_mode": TEST_MODE}


@app.post("/toggle_scheduler", response_class=JSONResponse)
async def toggle_scheduler(request: Request):
    global SCHEDULER_ENABLED
    if "user" not in request.session:
        return RedirectResponse(url="/login")

    SCHEDULER_ENABLED = not SCHEDULER_ENABLED
    set_key(ENV_FILE, "SCHEDULER_ENABLED", "true" if SCHEDULER_ENABLED else "false")
    return {"scheduler": SCHEDULER_ENABLED}

# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webui:app", host="0.0.0.0", port=WEBUI_PORT, reload=False)