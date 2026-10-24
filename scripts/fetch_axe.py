"""Optional one-time fetch of the upstream axe-core browser bundle."""
from pathlib import Path
from urllib.request import urlopen

URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.3/axe.min.js"
DEST = Path("app/engine/vendor/axe.min.js")
DEST.parent.mkdir(parents=True, exist_ok=True)
with urlopen(URL, timeout=30) as response:
    data = response.read()
if len(data) < 100_000:
    raise RuntimeError("Downloaded file looks unexpectedly small; refusing to save it.")
DEST.write_bytes(data)
print(f"Saved {len(data):,} bytes to {DEST}")
