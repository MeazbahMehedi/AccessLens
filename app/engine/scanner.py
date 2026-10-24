"""Rendered single-page accessibility checks with explicit coverage and review evidence."""

import asyncio
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from playwright.async_api import async_playwright
from app.core.config import settings
from app.core.security import validate_public_url, UnsafeURLError
from app.core.network import (
    ScanFailure,
    browser_proxy_options,
    can_retry_navigation,
    connection_failure,
)


@dataclass
class Finding:
    rule_id: str
    impact: str
    message: str
    selector: str = ""
    html: str = ""
    wcag_criteria: list[str] | None = None
    principle: str = "robust"
    wcag_level: str = "A"
    help_url: str = ""
    source: str = "custom"
    fix: str = ""
    category: str = "violation"


@dataclass
class PageResult:
    url: str
    title: str
    load_time_ms: int
    findings: list[Finding]
    screenshot_path: str | None = None
    notes: list[str] = field(default_factory=list)
    review_items: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


LEVELS = {"A": {"A"}, "AA": {"A", "AA"}, "AAA": {"A", "AA", "AAA"}}


def _level(tags):
    levels = [
        m.group(1).upper() for tag in tags if (m := re.fullmatch(r"wcag(?:2|21|22)(a{1,3})", tag))
    ]
    return max(levels, key=len) if levels else None


def axe_findings(results, level="AA"):
    failures, reviews, seen = [], [], set()
    for group in ("violations", "incomplete"):
        for rule in results.get(group, []):
            tags = rule.get("tags", [])
            rule_level = _level(tags)
            if rule_level and rule_level not in LEVELS[level]:
                continue
            criteria = [
                f"{m[1]}.{m[2]}.{m[3]}"
                for tag in tags
                if (m := re.fullmatch(r"wcag([1-4])(\d)(\d+)", tag))
            ]
            if not rule_level and "best-practice" not in tags:
                continue
            category = (
                "review"
                if group == "incomplete"
                else "best-practice"
                if not rule_level
                else "violation"
            )
            for node in rule.get("nodes", []):
                selector = " → ".join(
                    " → ".join(x) if isinstance(x, list) else str(x) for x in node.get("target", [])
                )
                key = (rule["id"], selector, category)
                if key in seen:
                    continue
                seen.add(key)
                item = finding_dict(
                    Finding(
                        rule_id=rule["id"],
                        impact=rule.get("impact") or "minor",
                        message=rule.get("help", rule["id"]),
                        selector=selector,
                        html=node.get("html", "")[:2000],
                        wcag_criteria=criteria,
                        principle={
                            "1": "perceivable",
                            "2": "operable",
                            "3": "understandable",
                            "4": "robust",
                        }.get((criteria or [""])[0][:1], "robust"),
                        wcag_level=rule_level or "—",
                        help_url=rule.get("helpUrl", ""),
                        source="axe-core",
                        fix=(
                            node.get("failureSummary")
                            or "Review this element in context; automatic evaluation was inconclusive."
                        ).strip(),
                        category=category,
                    )
                )
                (failures if category == "violation" else reviews).append(item)
    return failures, reviews


def _detect_challenge(title, page_text):
    title = title.lower().strip()
    text = page_text.lower()
    return any(
        x in title
        for x in (
            "just a moment",
            "checking your browser",
            "attention required!",
            "verify you are human",
        )
    ) or (
        len(text) < 2500
        and any(
            x in text
            for x in (
                "performing security verification",
                "enable javascript and cookies to continue",
                "verify you are human",
            )
        )
    )


async def scan_page(url, screenshot_path=None, wcag_level="AA"):
    if wcag_level not in LEVELS:
        raise ValueError("Invalid WCAG level")
    await asyncio.to_thread(validate_public_url, url)
    try:
        async with asyncio.timeout(settings.scan_timeout_seconds + 60):
            return await _scan(url, screenshot_path, wcag_level)
    except TimeoutError as exc:
        raise ScanFailure(
            "The overall scan time limit was reached. The page or its network requests took too long; no score was generated.",
            "scan_timeout",
            "scan",
        ) from exc


async def _scan(url, screenshot_path, wcag_level):
    start = time.monotonic()
    notes = []
    validated = {}
    navigation_errors = []
    blocked_resources = set()
    async with async_playwright() as p:
        proxy, proxy_source = browser_proxy_options()
        try:
            browser = await p.chromium.launch(
                headless=True, args=["--no-sandbox"], **({"proxy": proxy} if proxy else {})
            )
        except Exception as exc:
            raise connection_failure(exc) from exc
        context = await browser.new_context(
            viewport={"width": 1366, "height": 900}, service_workers="block", accept_downloads=False
        )

        async def guard(route):
            target = route.request.url
            if target.startswith(("data:", "blob:")):
                return await route.continue_()
            try:
                from urllib.parse import urlsplit

                origin = urlsplit(target).netloc
                if origin not in validated:
                    validated[origin] = asyncio.create_task(
                        asyncio.to_thread(validate_public_url, target)
                    )
                await validated[origin]
                await route.continue_()
            except Exception as exc:
                blocked_resources.add(target)
                if route.request.is_navigation_request() and route.request.frame == page.main_frame:
                    navigation_errors.append(exc)
                await route.abort("blockedbyclient")

        await context.route("**/*", guard)

        async def block_socket(socket):
            await socket.close()

        await context.route_web_socket("**/*", block_socket)
        page = await context.new_page()
        # Playwright routing does not intercept every hop in a redirect chain.
        # Pause Chromium responses and validate Location before it follows them.
        session = await context.new_cdp_session(page)
        main_frame_id = (await session.send("Page.getFrameTree"))["frameTree"]["frame"]["id"]

        async def check_redirect(event):
            from urllib.parse import urljoin

            request_id = event["requestId"]
            try:
                status = event.get("responseStatusCode", 0)
                if status in (301, 302, 303, 307, 308):
                    location = next(
                        (
                            h["value"]
                            for h in event.get("responseHeaders", [])
                            if h["name"].lower() == "location"
                        ),
                        None,
                    )
                    if location:
                        await asyncio.to_thread(
                            validate_public_url, urljoin(event["request"]["url"], location)
                        )
                await session.send("Fetch.continueResponse", {"requestId": request_id})
            except Exception as exc:
                blocked_resources.add(event["request"]["url"])
                if event.get("frameId") == main_frame_id:
                    navigation_errors.append(exc)
                try:
                    await session.send(
                        "Fetch.failRequest",
                        {"requestId": request_id, "errorReason": "BlockedByClient"},
                    )
                except Exception:
                    pass  # Browser shutdown may cancel an in-flight interception.

        session.on("Fetch.requestPaused", check_redirect)
        await session.send(
            "Fetch.enable", {"patterns": [{"urlPattern": "*", "requestStage": "Response"}]}
        )
        try:
            response = None
            for attempt in range(2):
                try:
                    response = await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=settings.scan_timeout_seconds * 1000,
                    )
                    break
                except Exception as exc:
                    if navigation_errors:
                        raise navigation_errors[-1] from exc
                    if attempt == 0 and can_retry_navigation(exc):
                        continue
                    raise connection_failure(exc) from exc
            if attempt:
                notes.append(
                    "A transient connection failed once; the page loaded on the second attempt."
                )
            if response and response.status >= 400:
                raise ScanFailure(
                    f"Website returned HTTP {response.status}; the intended page was not audited. The server may require login, reject automated visitors, or be unavailable.",
                    "http_error",
                    "page_access",
                )
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                notes.append(
                    "The page continued making requests. Results reflect the rendered state at capture time."
                )
            await page.wait_for_timeout(1000)
            final_url = await asyncio.to_thread(validate_public_url, page.url)
            title = await page.title()
            text = await page.locator("body").inner_text(timeout=5000)
            if _detect_challenge(title, text):
                raise ScanFailure(
                    "The site presented an anti-bot challenge. No accessibility score was generated for the intended page.",
                    "site_challenge",
                    "page_access",
                )
            if "consent" in final_url.lower() or "before you continue" in title.lower():
                notes.append(
                    "A consent page may be displayed. Review the screenshot; this report covers only that rendered state."
                )
            metadata = {
                "network_route": proxy_source,
                "final_url": final_url,
                "viewport": {"width": 1366, "height": 900},
                "coverage": "basic",
                "engine": "Basic checks",
                "passed_rules": 0,
                "inapplicable_rules": 0,
                "wcag_version": "2.2",
                "scoring_version": "2",
                "http_status": response.status if response else None,
            }
            failures = []
            reviews = []
            axe_path = Path(settings.axe_js_path)
            if axe_path.is_file():
                try:
                    await page.add_script_tag(path=str(axe_path))
                    tags = [
                        tag
                        for tag in (
                            "wcag2a",
                            "wcag2aa",
                            "wcag2aaa",
                            "wcag21a",
                            "wcag21aa",
                            "wcag21aaa",
                            "wcag22aa",
                        )
                        if _level([tag]) in LEVELS[wcag_level]
                    ] + ["best-practice"]
                    result = await page.evaluate(
                        "async tags => await axe.run(document,{runOnly:{type:'tag',values:tags}})",
                        tags,
                    )
                    failures, reviews = axe_findings(result, wcag_level)
                    metadata.update(
                        coverage="axe",
                        engine=f"axe-core {result.get('testEngine', {}).get('version', '')}",
                        passed_rules=len(result.get("passes", [])),
                        inapplicable_rules=len(result.get("inapplicable", [])),
                    )
                except Exception as exc:
                    notes.append(
                        f"axe-core could not complete ({type(exc).__name__}); only basic checks ran. Coverage is limited."
                    )
            else:
                notes.append(
                    "axe-core is missing. Only basic checks ran; contrast, ARIA and many WCAG criteria were not evaluated. Run python scripts/fetch_axe.py."
                )
            if metadata["coverage"] == "basic":
                basic = await page.evaluate(
                    Path(__file__).with_name("checks.js").read_text(encoding="utf-8")
                )
                failures = [x for x in basic if x["category"] == "violation"]
                reviews = [x for x in basic if x["category"] != "violation"]
            failures.sort(
                key=lambda x: (
                    {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}.get(x["impact"], 4),
                    x["rule_id"],
                )
            )
            shot = None
            if screenshot_path:
                try:
                    Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
                    selectors = [i["selector"] for i in failures if " → " not in i["selector"]][
                        :200
                    ]
                    await page.evaluate(
                        "selectors=>selectors.forEach(s=>{try{document.querySelectorAll(s).forEach(e=>{e.style.outline='3px solid #e24455';e.style.outlineOffset='2px'})}catch(e){}})",
                        selectors,
                    )
                    height = await page.evaluate(
                        "Math.min(Math.max(document.documentElement.scrollHeight,900),16000)"
                    )
                    await page.screenshot(
                        path=screenshot_path,
                        clip={"x": 0, "y": 0, "width": 1366, "height": height},
                        timeout=15000,
                    )
                    shot = screenshot_path
                except Exception:
                    notes.append(
                        "Screenshot capture failed; accessibility findings were saved successfully."
                    )
            if blocked_resources:
                notes.append(
                    f"{len(blocked_resources)} request(s) could not be publicly verified and were blocked. Some page content may be missing."
                )
            metadata["load_time_ms"] = int((time.monotonic() - start) * 1000)
            return PageResult(
                final_url,
                title,
                metadata["load_time_ms"],
                [Finding(**i) for i in failures],
                shot,
                notes,
                reviews,
                metadata,
            )
        finally:
            await browser.close()


def _run_in_own_loop(url, shot, level):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(scan_page(url, shot, level))
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


async def scan_page_isolated(url, screenshot_path=None, wcag_level="AA"):
    return await asyncio.to_thread(_run_in_own_loop, url, screenshot_path, wcag_level)


def run_scan(url, screenshot_path=None):
    return _run_in_own_loop(url, screenshot_path, "AA")


def finding_dict(finding):
    data = asdict(finding)
    data["wcag_criteria"] = data["wcag_criteria"] or []
    return data
