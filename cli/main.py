import asyncio
import json
import typer
from app.core.security import normalize_url
from app.engine.scanner import scan_page, finding_dict
from app.services.scoring import calculate_score

app = typer.Typer(help="AccessCheck command-line accessibility scanner")


@app.command()
def scan(url: str, fail_under: int = typer.Option(80, min=0, max=100), output: str = "text"):
    """Scan one public website URL."""
    if output not in {"text", "json"}:
        raise typer.BadParameter("Choose text or json for --output.")
    try:
        result = asyncio.run(scan_page(normalize_url(url)))
    except Exception as exc:
        typer.echo(f"Scan could not be completed: {exc}", err=True)
        raise typer.Exit(code=2)
    issues = [finding_dict(f) for f in result.findings]
    score = calculate_score(issues)
    if output == "json":
        typer.echo(
            json.dumps(
                {
                    "url": result.url,
                    "title": result.title,
                    "score": score,
                    "metadata": result.metadata,
                    "notes": result.notes,
                    "issues": issues,
                    "review_items": result.review_items,
                },
                indent=2,
            )
        )
    else:
        typer.echo(
            f"AccessCheck: {result.url}\nHeuristic score: {score}/100  Findings: {len(issues)}\nCoverage: {result.metadata.get('coverage', 'unknown')}"
        )
        for note in result.notes:
            typer.echo(f"Note: {note}")
        for issue in issues:
            typer.echo(f"- [{issue['impact']}] {issue['rule_id']}: {issue['message']}")
        typer.echo(
            f"{len(result.review_items)} manual-review / best-practice items. Automated results are not WCAG certification."
        )
    if score < fail_under:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
