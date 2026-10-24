import csv, io, json
from app.services.scoring import grade

def report_data(scan):
    return {
        "id": scan.id, "url": scan.url, "status": scan.status, "wcag_level": scan.wcag_level,
        "score": scan.score, "grade": grade(scan.score), "title": scan.title,
        "principle_scores": scan.principle_scores or {}, "issue_count": scan.issue_count,
        "severity_counts": {"critical":scan.critical_count,"serious":scan.serious_count,
          "moderate":scan.moderate_count,"minor":scan.minor_count},
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
        "issues": scan.issues or []
    }

def json_export(scan) -> bytes:
    return json.dumps(report_data(scan), indent=2).encode()

def csv_export(scan) -> bytes:
    out = io.StringIO()
    fields = ["rule_id","impact","message","selector","html","wcag_criteria","principle","wcag_level","fix","help_url"]
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for issue in scan.issues or []:
        writer.writerow({**issue, "wcag_criteria": ", ".join(issue.get("wcag_criteria", []))})
    return out.getvalue().encode("utf-8")

def pdf_export(scan) -> bytes:
    from weasyprint import HTML
    d = report_data(scan)
    issue_rows = "".join(
      f"<tr><td>{_esc(i.get('impact',''))}</td><td>{_esc(i.get('rule_id',''))}</td><td>{_esc(i.get('message',''))}</td><td>{_esc(', '.join(i.get('wcag_criteria',[])))}</td></tr>"
      for i in d["issues"])
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>AccessCheck report</title>
    <style>body{{font:14px sans-serif;margin:32px;color:#0f172a}}h1{{color:#1d4ed8}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #cbd5e1;padding:8px;text-align:left;vertical-align:top}}th{{background:#f1f5f9}}</style>
    <h1>AccessCheck Report</h1><p><b>Website:</b> {_esc(d['url'])}</p><p><b>Score:</b> {d['score']}/100 — {_esc(d['grade'])}</p>
    <p><b>Issues:</b> {d['issue_count']}</p><h2>Issues</h2><table><thead><tr><th>Impact</th><th>Rule</th><th>Issue</th><th>WCAG</th></tr></thead><tbody>{issue_rows}</tbody></table></html>"""
    return HTML(string=html).write_pdf()

def _esc(s):
    import html
    return html.escape(str(s))
