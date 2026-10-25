from pathlib import Path
from typing import Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "AccessLens"
    database_url: str = Field(default_factory=lambda: (
        "sqlite+aiosqlite:///./accesscheck.db"
        if Path("accesscheck.db").exists() and not Path("accesslens.db").exists()
        else "sqlite+aiosqlite:///./accesslens.db"
    ))
    scan_timeout_seconds: int = Field(default=45, ge=10, le=180)
    dns_public_fallback: bool = True
    dns_https_timeout_seconds: float = Field(default=8.0, ge=1, le=15)
    browser_proxy_url: SecretStr | None = None
    browser_proxy_mode: Literal["auto", "system"] = "auto"
    screenshot_dir: str = str(ROOT / "app/web/static/screenshots")
    axe_js_path: str = str(ROOT / "app/engine/vendor/axe.min.js")
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
