"""Download-once cache. Downloaded files are data only: they are read, never
executed or extracted to disk (zip members are read in memory)."""
import hashlib
import io
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

CACHE = Path(__file__).resolve().parents[2] / "data" / "cache"


def fetch(source_id: str, url: str, filename: str) -> tuple[bytes, str]:
    d = CACHE / source_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / filename
    if not path.exists():
        print(f"  downloading {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "bible-app-ingest/0.1"})
        with urllib.request.urlopen(req, timeout=120) as r:
            path.write_bytes(r.read())
    data = path.read_bytes()
    return data, hashlib.sha256(data).hexdigest()


def zip_member(data: bytes, endswith: str) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if n.endswith(endswith)]
        if len(names) != 1:
            raise RuntimeError(f"expected one member ending {endswith!r}, found {names}")
        return z.read(names[0]).decode("utf-8-sig")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
