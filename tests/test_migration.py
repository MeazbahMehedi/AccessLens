import sqlite3
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from app import db


@pytest.mark.asyncio
async def test_old_sqlite_is_upgraded_without_losing_records(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE scans (id VARCHAR(36) PRIMARY KEY, status VARCHAR(16))")
        c.execute("INSERT INTO scans VALUES ('old','done')")
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    monkeypatch.setattr(db, "engine", engine)
    await db.init_db()
    await engine.dispose()
    with sqlite3.connect(path) as c:
        columns = {x[1] for x in c.execute("PRAGMA table_info(scans)")}
        assert {"review_items", "scan_metadata"} <= columns
        assert c.execute("SELECT id, review_items, scan_metadata FROM scans").fetchone() == (
            "old",
            "[]",
            "{}",
        )
