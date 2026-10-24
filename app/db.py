from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import String, Integer, Text, DateTime, JSON, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings


class Base(DeclarativeBase):
    pass


class Scan(Base):
    __tablename__ = "scans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    wcag_level: Mapped[str] = mapped_column(String(3), default="AA")
    score: Mapped[int] = mapped_column(Integer, default=100)
    principle_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    title: Mapped[str] = mapped_column(Text, default="")
    issue_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    serious_count: Mapped[int] = mapped_column(Integer, default=0)
    moderate_count: Mapped[int] = mapped_column(Integer, default=0)
    minor_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_items: Mapped[list] = mapped_column(JSON, default=list)
    scan_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    issues: Mapped[list] = mapped_column(JSON, default=list)


engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    if settings.database_url.startswith("sqlite"):
        Path(settings.screenshot_dir).mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        if settings.database_url.startswith("sqlite"):
            columns = await conn.run_sync(
                lambda c: {x["name"] for x in inspect(c).get_columns("scans")}
            )
            for name, default in (("review_items", "[]"), ("scan_metadata", "{}")):
                if name not in columns:
                    await conn.execute(
                        text(
                            f"ALTER TABLE scans ADD COLUMN {name} JSON NOT NULL DEFAULT '{default}'"
                        )
                    )
