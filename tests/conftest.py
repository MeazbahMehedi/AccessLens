import os
import tempfile
from pathlib import Path

_temp = Path(tempfile.mkdtemp(prefix="accesscheck-tests-"))
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_temp / 'test.db'}"
os.environ["SCREENSHOT_DIR"] = str(_temp / "screenshots")

# Controlled local browser fixtures must not inherit this runner's external proxy.
os.environ["BROWSER_PROXY_MODE"] = "system"
os.environ.pop("BROWSER_PROXY_URL", None)
