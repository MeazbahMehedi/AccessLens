"""Restore the pinned upstream axe-core bundle and license (setup only)."""

from pathlib import Path
from urllib.request import urlopen

VERSION = "4.10.3"
DEST = Path(__file__).resolve().parents[1] / "app/engine/vendor"


def main():
    with urlopen(
        f"https://cdnjs.cloudflare.com/ajax/libs/axe-core/{VERSION}/axe.min.js", timeout=30
    ) as response:
        data = response.read()
    if len(data) < 100_000 or b"axe" not in data[:5000]:
        raise RuntimeError("Unexpected axe-core bundle; refusing to save it.")
    with urlopen(f"https://unpkg.com/axe-core@{VERSION}/LICENSE", timeout=30) as response:
        license_data = response.read()
    if b"Mozilla Public License" not in license_data:
        raise RuntimeError("Unexpected license content; refusing to save it.")
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "axe.min.js").write_bytes(data)
    (DEST / "AXE-LICENSE.txt").write_bytes(license_data)
    print(f"Saved axe-core {VERSION} ({len(data):,} bytes) and its MPL 2.0 license.")


if __name__ == "__main__":
    main()
