import asyncio, json, typer
from app.engine.scanner import scan_page, finding_dict
from app.services.scoring import calculate_score

app = typer.Typer(help="AccessCheck command-line accessibility scanner")

@app.command()
def scan(url: str, fail_under: int = 80, output: str = "text"):
    """Scan one public website URL."""
    result = asyncio.run(scan_page(url))
    issues = [finding_dict(f) for f in result.findings]
    score = calculate_score(issues)
    if output == "json":
        typer.echo(json.dumps({"url":result.url,"title":result.title,"score":score,"issues":issues}, indent=2))
    else:
        typer.echo(f"AccessCheck: {result.url}\nScore: {score}/100  Issues: {len(issues)}")
        for issue in issues:
            typer.echo(f"- [{issue['impact']}] {issue['rule_id']}: {issue['message']}")
    if score < fail_under:
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
