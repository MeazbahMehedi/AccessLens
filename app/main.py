import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, update
from app.core.config import settings
from app.core.network import ScanFailure
from app.core.security import (
    validate_public_url,
    normalize_url,
    UnsafeURLError,
    DNSVerificationError,
)
from app.db import init_db, SessionLocal, Scan
from app.engine.scanner import scan_page_isolated, finding_dict
from app.services.scoring import calculate_score, principle_scores, grade, PRINCIPLES
from app.services.report_service import json_export, csv_export, pdf_export, docx_export, doc_export
from app.services.github_service import developer_data

BASE = Path(__file__).parent
Path(settings.screenshot_dir).mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(BASE / "web" / "templates"))
templates.env.globals["grade"] = grade
_tasks = set()
_slots = asyncio.Semaphore(2)


@asynccontextmanager
async def lifespan(app):
    await init_db()
    async with SessionLocal() as db:
        await db.execute(
            update(Scan)
            .where(Scan.status.in_(["queued", "running"]))
            .values(status="failed", error="Interrupted by a server restart. Please scan again.")
        )
        await db.commit()
    yield
    for task in tuple(_tasks):
        task.cancel()
    if _tasks:
        await asyncio.gather(*_tasks, return_exceptions=True)


app = FastAPI(
    title="AccessLens",
    version="2.0.2",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.mount("/static", StaticFiles(directory=str(BASE / "web" / "static")), name="static")
app.mount("/screenshots", StaticFiles(directory=settings.screenshot_dir), name="screenshots")


async def run_and_save(scan_id):
    async with _slots, SessionLocal() as db:
        scan = await db.get(Scan, scan_id)
        if not scan:
            return
        scan.status = "running"
        scan.error = None
        await db.commit()
        try:
            result = await scan_page_isolated(
                scan.url, str(Path(settings.screenshot_dir) / f"{scan.id}.png"), scan.wcag_level
            )
            issues = [finding_dict(i) for i in result.findings]
            scan.title = result.title
            scan.issues = issues
            scan.review_items = result.review_items
            scan.scan_metadata = result.metadata
            scan.screenshot_path = f"/screenshots/{scan.id}.png" if result.screenshot_path else None
            scan.issue_count = len(issues)
            for impact in ("critical", "serious", "moderate", "minor"):
                setattr(scan, impact + "_count", sum(i["impact"] == impact for i in issues))
            scan.score = calculate_score(issues)
            scan.principle_scores = principle_scores(issues)
            scan.error = " ".join(result.notes) or None
            scan.status = "done"
        except Exception as exc:
            logging.exception("Scan failed: %s", scan_id)
            scan.status = "failed"
            scan.error = (
                str(exc)[:700]
                if isinstance(exc, (UnsafeURLError, ScanFailure))
                else f"{type(exc).__name__}: {exc}"[:700]
            )
            scan.scan_metadata = {
                "error_code": getattr(exc, "code", "scan_failed"),
                "stage": getattr(exc, "stage", "scan"),
            }
            scan.screenshot_path = None
        scan.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def create_scan(url, wcag_level="AA"):
    if wcag_level not in {"A", "AA", "AAA"}:
        raise HTTPException(422, "Choose WCAG level A, AA, or AAA.")
    if len(url) > 4096:
        raise HTTPException(422, "The URL is too long.")
    if len(_tasks) >= 20:
        raise HTTPException(429, "The scan queue is full. Please wait for a scan to finish.")
    try:
        safe_url = await asyncio.to_thread(validate_public_url, normalize_url(url))
    except DNSVerificationError as exc:
        raise HTTPException(503, str(exc)) from exc
    except UnsafeURLError as exc:
        raise HTTPException(422, str(exc)) from exc
    scan_id = str(uuid4())
    async with SessionLocal() as db:
        db.add(Scan(id=scan_id, url=safe_url, status="queued", wcag_level=wcag_level))
        await db.commit()
    task = asyncio.create_task(run_and_save(scan_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return scan_id


def render(request, name, **context):
    return templates.TemplateResponse(request, name, {"request": request, **context})


async def all_scans():
    async with SessionLocal() as db:
        return (await db.scalars(select(Scan).order_by(Scan.created_at.desc()))).all()


def dashboard_data(scans):
    done = [
        s
        for s in scans
        if s.status == "done" and (s.scan_metadata or {}).get("scoring_version") == "2"
    ]
    severity = {
        k: sum(getattr(s, k + "_count") for s in done)
        for k in ("critical", "serious", "moderate", "minor")
    }
    trend = [
        {
            "label": s.created_at.strftime("%m/%d %H:%M"),
            "score": s.score,
            "url": s.url,
            "level": s.wcag_level,
        }
        for s in reversed(done[:12])
    ]
    return {
        "total": len(scans),
        "completed": len(done),
        "failed": sum(s.status == "failed" for s in scans),
        "active": sum(s.status in ("queued", "running") for s in scans),
        "avg": round(sum(s.score for s in done) / len(done)) if done else None,
        "issues": sum(s.issue_count for s in done),
        "reviews": sum(len(s.review_items or []) for s in done),
        "severity": severity,
        "trend": trend,
        "principles": {
            p: round(sum((s.principle_scores or {}).get(p, 100) for s in done) / len(done))
            if done
            else None
            for p in PRINCIPLES
        },
    }


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    scans = await all_scans()
    return render(
        request, "dashboard.html", active="dashboard", scans=scans[:6], stats=dashboard_data(scans)
    )


@app.get("/new-scan", response_class=HTMLResponse)
async def home(request: Request):
    return render(request, "home.html", active="scan", error=None)


@app.post("/scan", response_class=HTMLResponse)
async def web_scan(request: Request, url: str = Form(...), wcag_level: str = Form("AA")):
    try:
        scan_id = await create_scan(url, wcag_level)
    except HTTPException as exc:
        return templates.TemplateResponse(
            request,
            "home.html",
            {
                "request": request,
                "active": "scan",
                "error": exc.detail,
                "entered_url": url,
                "selected_level": wcag_level,
            },
            status_code=exc.status_code,
        )
    return RedirectResponse(f"/scan/{scan_id}", status_code=303)


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request, q: str = "", status: str = "all", page: int = 1):
    scans = await all_scans()
    filtered = [
        s
        for s in scans
        if (status == "all" or s.status == status)
        and q.lower() in (s.url + " " + (s.title or "")).lower()
    ]
    pages = max(1, (len(filtered) + 19) // 20)
    page = max(1, min(page, pages))
    return render(
        request,
        "history.html",
        active="history",
        scans=filtered[(page - 1) * 20 : page * 20],
        q=q,
        status=status,
        page=page,
        pages=pages,
        total=len(filtered),
    )


@app.get("/reports", response_class=HTMLResponse)
async def reports(request: Request):
    return render(
        request,
        "reports.html",
        active="reports",
        scans=[s for s in await all_scans() if s.status == "done"],
    )


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return render(request, "about.html", active="about")


@app.get("/developer", response_class=HTMLResponse)
async def developer(request: Request):
    return render(request, "developer.html", active="developer")


@app.get("/internal/developer")
async def github():
    return await developer_data()


@app.get("/internal/dashboard")
async def live_dashboard():
    return dashboard_data(await all_scans())


@app.get("/scan/{scan_id}", response_class=HTMLResponse)
async def results(request: Request, scan_id: str):
    async with SessionLocal() as db:
        scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    return render(
        request,
        "results.html",
        active="history",
        scan=scan,
        issues=scan.issues or [],
        reviews=scan.review_items or [],
        meta=scan.scan_metadata or {},
    )


@app.get("/internal/scans/{scan_id}/status")
async def scan_status(scan_id: str):
    async with SessionLocal() as db:
        scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    return {"status": scan.status, "error": scan.error}


@app.get("/scan/{scan_id}/export")
async def export(scan_id: str, format: str = "json"):
    formats = {
        "json": (json_export, "application/json"),
        "csv": (csv_export, "text/csv; charset=utf-8"),
        "pdf": (pdf_export, "application/pdf"),
        "docx": (
            docx_export,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        "doc": (doc_export, "application/msword"),
    }
    if format not in formats:
        raise HTTPException(400, "Choose pdf, docx, doc, csv, or json.")
    async with SessionLocal() as db:
        scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.status != "done":
        raise HTTPException(409, "Reports are available after a scan completes successfully.")
    fn, mime = formats[format]
    try:
        data = await asyncio.to_thread(fn, scan)
    except Exception as exc:
        logging.exception("Export failed")
        raise HTTPException(
            500, "Report generation failed. Check the server log and installed dependencies."
        ) from exc
    return Response(
        data,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="accesslens-{scan.id}.{format}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok", "app": "AccessLens", "version": "2.0.2"}


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse(
        request, "404.html", {"request": request, "active": ""}, status_code=404
    )
