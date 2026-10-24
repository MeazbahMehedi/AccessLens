import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4, UUID
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select, update
from app.core.config import settings
from app.core.security import validate_public_url, normalize_url, UnsafeURLError
from app.db import init_db, SessionLocal, Scan
from app.engine.scanner import scan_page_isolated, finding_dict
from app.services.scoring import calculate_score, principle_scores
from app.services.report_service import json_export, csv_export, pdf_export, report_data

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "web" / "templates"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # scans left 'queued'/'running' by a previous crash/restart would spin forever
    async with SessionLocal() as db:
        await db.execute(update(Scan).where(Scan.status.in_(["queued", "running"]))
                         .values(status="failed", error="Interrupted by a server restart. Please scan again."))
        await db.commit()
    yield

app = FastAPI(title="AccessCheck", description="Local-first WCAG accessibility scanner", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE / "web" / "static")), name="static")

_tasks: set = set()
_slots = asyncio.Semaphore(2)  # at most 2 browsers at once

class ScanRequest(BaseModel):
    url: HttpUrl
    wcag_level: str = "AA"

async def run_and_save(scan_id: str):
    async with _slots, SessionLocal() as db:
        scan = await db.get(Scan, scan_id)
        if not scan:
            return
        scan.status = "running"
        scan.error = None
        await db.commit()
        try:
            shot = str(Path(settings.screenshot_dir) / f"{scan.id}.png")
            result = await scan_page_isolated(scan.url, shot, scan.wcag_level)
            issues = [finding_dict(f) for f in result.findings]
            scan.title = result.title
            scan.screenshot_path = f"/static/screenshots/{scan.id}.png"
            scan.issues = issues
            scan.issue_count = len(issues)
            scan.critical_count = sum(i["impact"] == "critical" for i in issues)
            scan.serious_count = sum(i["impact"] == "serious" for i in issues)
            scan.moderate_count = sum(i["impact"] == "moderate" for i in issues)
            scan.minor_count = sum(i["impact"] == "minor" for i in issues)
            scan.score = calculate_score(issues)
            scan.principle_scores = principle_scores(issues)
            scan.error = " ".join(result.notes or []) or None  # non-fatal warnings
            scan.status = "done"
        except Exception as exc:
            import traceback
            traceback.print_exc()
            print("SCAN ERROR TYPE:", type(exc).__module__, type(exc).__name__)
            print("SCAN ERROR DETAILS:", repr(exc))
            scan.status = "failed"
            scan.error = (f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__)[:500]
            scan.screenshot_path = None
        scan.completed_at = datetime.now(timezone.utc)
        await db.commit()

async def create_scan(url: str, wcag_level: str = "AA"):
    try: safe_url = await asyncio.to_thread(validate_public_url, normalize_url(url))
    except UnsafeURLError as exc: raise HTTPException(422, str(exc))
    if wcag_level not in {"A","AA","AAA"}: raise HTTPException(422, "wcag_level must be A, AA, or AAA")
    scan_id = str(uuid4())
    async with SessionLocal() as db:
        db.add(Scan(id=scan_id, url=safe_url, status="queued", wcag_level=wcag_level))
        await db.commit()
    task = asyncio.create_task(run_and_save(scan_id))  # run in background; page polls status
    _tasks.add(task); task.add_done_callback(_tasks.discard)
    return scan_id

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {"request":request, "error":None})

@app.post("/scan", response_class=HTMLResponse)
async def web_scan(request: Request, url: str = Form(...), wcag_level: str = Form("AA")):
    try:
        scan_id = await create_scan(url, wcag_level)
    except HTTPException as exc:
        return templates.TemplateResponse(request, "home.html", {"request":request, "error":str(exc.detail)}, status_code=exc.status_code)
    return RedirectResponse(f"/scan/{scan_id}", status_code=303)

@app.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    async with SessionLocal() as db:
        scans = (await db.scalars(select(Scan).order_by(Scan.created_at.desc()).limit(100))).all()
    done = [s for s in scans if s.status == "done"]
    stats = {"total": len(scans), "avg": round(sum(s.score for s in done)/len(done)) if done else 0,
             "issues": sum(s.issue_count for s in done), "critical": sum(s.critical_count for s in done)}
    return templates.TemplateResponse(request, "history.html", {"request":request,"scans":scans,"stats":stats})

@app.get("/scan/{scan_id}", response_class=HTMLResponse)
async def results(request: Request, scan_id: str):
    async with SessionLocal() as db:
        scan = await db.get(Scan, scan_id)
    if not scan: raise HTTPException(404, "Scan not found")
    return templates.TemplateResponse(request, "results.html", {"request":request,"scan":scan,"issues":scan.issues or []})

@app.get("/scan/{scan_id}/export")
async def export(scan_id: str, format: str = "json"):
    async with SessionLocal() as db: scan = await db.get(Scan, scan_id)
    if not scan: raise HTTPException(404, "Scan not found")
    if format == "json": return Response(json_export(scan), media_type="application/json", headers={"Content-Disposition":f'attachment; filename="accesscheck-{scan_id}.json"'})
    if format == "csv": return Response(csv_export(scan), media_type="text/csv", headers={"Content-Disposition":f'attachment; filename="accesscheck-{scan_id}.csv"'})
    if format == "pdf":
        try: data = pdf_export(scan)
        except Exception as exc: raise HTTPException(500, f"PDF export failed; check WeasyPrint system dependencies: {exc}")
        return Response(data, media_type="application/pdf", headers={"Content-Disposition":f'attachment; filename="accesscheck-{scan_id}.pdf"'})
    raise HTTPException(400, "format must be json, csv, or pdf")

@app.post("/api/scans", status_code=202)
async def api_create_scan(body: ScanRequest):
    scan_id = await create_scan(str(body.url), body.wcag_level)
    return {"id":scan_id,"status":"queued","url":f"/scan/{scan_id}","poll":f"/api/scans/{scan_id}"}

@app.get("/api/scans/{scan_id}/status")
async def api_scan_status(scan_id: str):
    async with SessionLocal() as db: scan = await db.get(Scan, scan_id)
    if not scan: raise HTTPException(404, "Scan not found")
    return {"status": scan.status, "error": scan.error}

@app.get("/api/scans/{scan_id}")
async def api_get_scan(scan_id: str):
    async with SessionLocal() as db: scan = await db.get(Scan, scan_id)
    if not scan: raise HTTPException(404, "Scan not found")
    return report_data(scan)

@app.get("/health")
async def health():
    return {"status":"ok","app":"AccessCheck"}

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)
