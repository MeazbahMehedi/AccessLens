import csv, io, json
from datetime import datetime, timezone
from types import SimpleNamespace
from zipfile import ZipFile
from pypdf import PdfReader
from app.services.report_service import json_export, csv_export, pdf_export, docx_export, doc_export


def sample():
    issue = {
        "rule_id": "image-alt",
        "impact": "serious",
        "message": "Image missing alt <unsafe>",
        "selector": "#img",
        "html": '<img src="example.png">',
        "wcag_criteria": ["1.1.1"],
        "principle": "perceivable",
        "wcag_level": "A",
        "fix": "Add meaningful alt.",
        "help_url": "https://example.com/",
        "source": "axe-core",
        "category": "violation",
        "unexpected_future_field": "test",
    }
    return SimpleNamespace(
        id="test",
        url="https://example.com",
        title="Test 演示",
        status="done",
        wcag_level="AA",
        score=93,
        principle_scores={"perceivable": 93},
        issue_count=1,
        critical_count=0,
        serious_count=1,
        moderate_count=0,
        minor_count=0,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        issues=[issue],
        review_items=[],
        scan_metadata={"coverage": "axe"},
        error=None,
    )


def test_json_roundtrip():
    d = json.loads(json_export(sample()))
    assert d["issues"][0]["source"] == "axe-core"
    assert "limitations" in d
    assert d["title"] == "Test 演示"


def test_csv_source_extra_fields_and_formula_protection():
    s = sample()
    s.issues[0]["message"] = "=SUM(1,2)"
    rows = list(csv.DictReader(io.StringIO(csv_export(s).decode("utf-8-sig"))))
    assert rows[0]["source"] == "axe-core"
    assert rows[0]["message"].startswith("'=")


def test_pdf_is_readable_and_contains_evidence():
    data = pdf_export(sample())
    assert data.startswith(b"%PDF")
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(data)).pages)
    assert "image-alt" in text
    assert "example.com" in text


def test_docx_contains_report():
    data = docx_export(sample())
    z = ZipFile(io.BytesIO(data))
    xml = z.read("word/document.xml").decode()
    assert "image-alt" in xml
    assert "&lt;img" in xml
    assert "Test 演示" in xml


def test_legacy_doc_is_word_compatible_rtf():
    assert doc_export(sample()).startswith(b"{\\rtf1")


def test_empty_csv_still_identifies_scan():
    s = sample()
    s.issues = []
    s.issue_count = 0
    rows = list(csv.DictReader(io.StringIO(csv_export(s).decode("utf-8-sig"))))
    assert rows[0]["scan_id"] == "test"
    assert rows[0]["category"] == "summary"


def test_multipage_pdf_and_unicode():
    s = sample()
    s.issues = s.issues * 35
    s.issues[0]["fix"] = "Long evidence " * 500 + "演示"
    data = pdf_export(s)
    assert len(PdfReader(io.BytesIO(data)).pages) > 1
