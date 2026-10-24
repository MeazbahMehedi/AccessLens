
"""Browser scanner. Kept independent of FastAPI and database code."""

import asyncio
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from playwright.async_api import async_playwright

from app.core.config import settings
from app.core.security import validate_public_url


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


@dataclass
class PageResult:
    url: str
    title: str
    load_time_ms: int
    findings: list[Finding]
    screenshot_path: str | None = None


def _safe_target(url: str):
    """Validate a public URL using the shared security module."""
    return validate_public_url(url)


def _detect_challenge(title: str, page_text: str) -> bool:
    """Return True when a recognizable anti-bot challenge is displayed."""
    title_lower = title.lower()
    text_lower = page_text.lower()

    challenge_markers = [
        "just a moment...",
        "checking your browser",
        "verify you are human",
        "performing security verification",
        "enable javascript and cookies to continue",
    ]

    return any(
        marker in title_lower or marker in text_lower
        for marker in challenge_markers
    )


async def scan_page(
    url: str, screenshot_path: str | None = None
) -> PageResult:
    _safe_target(url)

    start = time.monotonic()
    findings: list[Finding] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"],
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 900}
        )
        page = await context.new_page()

        try:
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=settings.scan_timeout_seconds * 1000,
            )

            final_url = page.url
            _safe_target(final_url)

            title = await page.title()
            page_text = ""

            try:
                page_text = (
                    await page.locator("body").inner_text(timeout=5000)
                ).lower()
            except Exception:
                # The page may not expose readable body text.
                pass

            if _detect_challenge(title, page_text):
                raise RuntimeError(
                    "Scan blocked: The website presented an anti-bot "
                    "security challenge. The actual page could not be "
                    "inspected, so accessibility findings are unavailable."
                )

            load_ms = int((time.monotonic() - start) * 1000)

            axe_path = Path(settings.axe_js_path)

            if axe_path.exists():
                await page.add_script_tag(path=str(axe_path))
                axe = await page.evaluate(
                    """async () =>
                        await axe.run(document, {
                            resultTypes: ['violations']
                        })
                    """
                )

                for violation in axe.get("violations", []):
                    tags = violation.get("tags", [])
                    criteria = []

                    for tag in tags:
                        if (
                            tag.startswith("wcag")
                            and len(tag) >= 7
                            and tag[4].isdigit()
                        ):
                            digits = tag[4:]
                            if (
                                len(digits) >= 3
                                and digits[:3].isdigit()
                            ):
                                criteria.append(
                                    f"{digits[0]}.{digits[1]}.{digits[2:]}"
                                )

                    first = criteria[0] if criteria else ""
                    principle = {
                        "1": "perceivable",
                        "2": "operable",
                        "3": "understandable",
                        "4": "robust",
                    }.get(first[:1], "robust")

                    for node in violation.get("nodes", []):
                        findings.append(
                            Finding(
                                rule_id=violation["id"],
                                impact=violation.get("impact") or "minor",
                                message=(
                                    violation.get("help")
                                    or violation["id"]
                                ),
                                selector=", ".join(
                                    str(x)
                                    for x in node.get("target", [])
                                ),
                                html=node.get("html", ""),
                                wcag_criteria=criteria,
                                principle=principle,
                                wcag_level=(
                                    "AA"
                                    if any("aa" in x for x in tags)
                                    else "A"
                                ),
                                help_url=violation.get("helpUrl", ""),
                                source="axe",
                            )
                        )

            custom = await page.evaluate(
                """() => {
                    const out = [];

                    const add = (
                        rule, impact, message, el,
                        wcag, principle, fix
                    ) => out.push({
                        rule_id: rule,
                        impact,
                        message,
                        selector: el
                            ? (el.id
                                ? '#' + CSS.escape(el.id)
                                : el.tagName.toLowerCase())
                            : 'html',
                        html: el ? el.outerHTML.slice(0, 500) : '',
                        wcag_criteria: wcag,
                        principle,
                        wcag_level: 'A',
                        source: 'custom',
                        fix
                    });

                    if (!document.documentElement.lang) {
                        add(
                            'page-lang', 'serious',
                            'Document language is missing.',
                            document.documentElement,
                            ['3.1.1'], 'understandable',
                            'Add a correct lang attribute, e.g. <html lang="en">.'
                        );
                    }

                    if (!document.title.trim()) {
                        add(
                            'page-title', 'serious',
                            'Page title is missing or empty.',
                            document.querySelector('head title'),
                            ['2.4.2'], 'operable',
                            'Add a concise, descriptive <title>.'
                        );
                    }

                    const headings = [
                        ...document.querySelectorAll(
                            'h1,h2,h3,h4,h5,h6'
                        )
                    ];

                    if (!headings.some(h => h.tagName === 'H1')) {
                        add(
                            'heading-h1', 'moderate',
                            'Page has no level-one heading.',
                            document.querySelector('main') || document.body,
                            ['1.3.1', '2.4.6'], 'perceivable',
                            'Add one descriptive <h1> for the main page heading.'
                        );
                    }

                    for (const el of document.querySelectorAll('img')) {
                        if (!el.hasAttribute('alt')) {
                            add(
                                'image-alt', 'serious',
                                'Image is missing an alt attribute.',
                                el, ['1.1.1'], 'perceivable',
                                'Add meaningful alt text, or alt="" for decorative images.'
                            );
                        }
                    }

                    for (const el of document.querySelectorAll(
                        'input:not([type=hidden]),select,textarea'
                    )) {
                        if (
                            !el.labels?.length &&
                            !el.getAttribute('aria-label') &&
                            !el.getAttribute('aria-labelledby')
                        ) {
                            add(
                                'form-label', 'serious',
                                'Form control has no programmatic label.',
                                el, ['3.3.2', '4.1.2'],
                                'understandable',
                                'Associate a <label for="..."> with the control or provide an accessible name.'
                            );
                        }
                    }

                    for (const el of document.querySelectorAll('a,button')) {
                        const text = (
                            el.innerText ||
                            el.getAttribute('aria-label') ||
                            ''
                        ).trim().toLowerCase();

                        if (!text) {
                            add(
                                'link-name', 'serious',
                                'Link or button has no accessible name.',
                                el, ['2.4.4', '4.1.2'], 'operable',
                                'Add descriptive visible text or an accessible name.'
                            );
                        } else if (
                            el.tagName === 'A' &&
                            ['click here', 'read more', 'here', 'more'].includes(text)
                        ) {
                            add(
                                'link-purpose', 'moderate',
                                'Link text may not explain its destination.',
                                el, ['2.4.4'], 'operable',
                                'Use link text that describes the destination or action.'
                            );
                        }
                    }

                    if (!document.querySelector('main,[role=main]')) {
                        add(
                            'main-landmark', 'moderate',
                            'Page has no main landmark.',
                            document.body, ['1.3.1'], 'perceivable',
                            'Wrap primary content in <main>.'
                        );
                    }

                    for (const el of document.querySelectorAll(
                        'a,button,input,select,textarea,[role=button]'
                    )) {
                        const rect = el.getBoundingClientRect();

                        if (
                            rect.width &&
                            rect.height &&
                            (rect.width < 24 || rect.height < 24)
                        ) {
                            add(
                                'target-size', 'minor',
                                'Interactive target is smaller than 24 by 24 CSS pixels.',
                                el, ['2.5.8'], 'operable',
                                'Increase the target to at least 24×24 CSS pixels or provide sufficient spacing.'
                            );
                        }
                    }

                    return out;
                }"""
            )

            existing = {
                (finding.rule_id, finding.selector)
                for finding in findings
            }

            for item in custom:
                key = (item["rule_id"], item["selector"])
                if key not in existing:
                    findings.append(Finding(**item))
                    existing.add(key)

            if screenshot_path:
                Path(screenshot_path).parent.mkdir(
                    parents=True, exist_ok=True
                )

                selectors = [
                    finding.selector
                    for finding in findings
                    if finding.selector
                    and not finding.selector.startswith("html")
                ]

                await page.evaluate(
                    """(selectors) => {
                        for (const selector of selectors) {
                            try {
                                document.querySelectorAll(selector)
                                    .forEach(el => {
                                        el.style.outline =
                                            '3px solid #d92d20';
                                        el.style.outlineOffset = '2px';
                                    });
                            } catch (_) {}
                        }
                    }""",
                    selectors,
                )

                await page.screenshot(
                    path=screenshot_path,
                    full_page=True,
                )

            return PageResult(
                final_url,
                title,
                load_ms,
                findings,
                screenshot_path,
            )

        except Exception as exc:
            print(
                f"[AccessCheck] Scan failed for {url}: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            raise

        finally:
            await browser.close()


def run_scan(
    url: str, screenshot_path: str | None = None
) -> PageResult:
    return asyncio.run(scan_page(url, screenshot_path))


def finding_dict(finding: Finding) -> dict:
    data = asdict(finding)
    data["wcag_criteria"] = data["wcag_criteria"] or []
    return data
