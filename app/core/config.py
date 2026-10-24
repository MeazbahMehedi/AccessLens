from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AccessCheck"
    database_url: str = "sqlite+aiosqlite:///./accesscheck.db"
    redis_url: str = "redis://localhost:6379/0"
    scan_timeout_seconds: int = 45
    max_pages_limit: int = 5
    screenshot_dir: str = "app/web/static/screenshots"
    axe_js_path: str = "app/engine/vendor/axe.min.js"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
