"""Fact registry for the workbook.

Nothing numeric goes into the book unless it came through here first. Each
record keeps the value, the exact request that produced it, the raw response on
disk, and the date it was retrieved, so the dataset index at the back of the
book can state when every claim was last checked against the live source.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "research" / "facts.jsonl"
RAW = ROOT / "research" / "raw"
DATA = ROOT / "data"

UA = "no-lab-required-workbook/1.0 (https://github.com/rikhinkavuru/NoLabRequired; rikhin@virahacks.com)"
_last_call = {"t": 0.0}


def _throttle(min_gap: float = 0.40) -> None:
    """NCBI allows 3 requests a second without a key; stay well under it."""
    gap = time.monotonic() - _last_call["t"]
    if gap < min_gap:
        time.sleep(min_gap - gap)
    _last_call["t"] = time.monotonic()


def fetch(url: str, *, params: dict | None = None, retries: int = 4, binary: bool = False):
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        _throttle()
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read()
                return (body if binary else body.decode("utf-8", "replace")), url
        except Exception as exc:  # noqa: BLE001 - retry on anything transient
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries} tries: {url}\n{last}")


def save_raw(name: str, text: str | bytes) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / name
    mode = "wb" if isinstance(text, bytes) else "w"
    with open(path, mode) as fh:
        fh.write(text)
    return path


def _load() -> dict[str, dict]:
    if not FACTS.exists():
        return {}
    out = {}
    with open(FACTS) as fh:
        for line in fh:
            line = line.strip()
            if line:
                rec = json.loads(line)
                out[rec["id"]] = rec
    return out


def _write(records: dict[str, dict]) -> None:
    FACTS.parent.mkdir(parents=True, exist_ok=True)
    with open(FACTS, "w") as fh:
        for key in sorted(records):
            fh.write(json.dumps(records[key], ensure_ascii=False) + "\n")


def record(
    fact_id: str,
    value,
    *,
    source_url: str,
    method: str,
    raw_file: str | None = None,
    note: str = "",
    unit: str = "",
) -> None:
    """Register one verified fact, overwriting any earlier value for the same id."""
    records = _load()
    records[fact_id] = {
        "id": fact_id,
        "value": value,
        "unit": unit,
        "source_url": source_url,
        "method": method,
        "raw_file": raw_file or "",
        "note": note,
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    _write(records)


def get(fact_id: str):
    return _load().get(fact_id)


def all_facts() -> dict[str, dict]:
    return _load()


def save_data(relative: str, content: str | bytes) -> Path:
    path = DATA / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    with open(path, mode) as fh:
        fh.write(content)
    digest = hashlib.sha256(
        content if isinstance(content, bytes) else content.encode()
    ).hexdigest()
    return path, digest


# --- service wrappers -------------------------------------------------------

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def eutils(endpoint: str, **params):
    params.setdefault("tool", "no-lab-required-workbook")
    params.setdefault("email", "rikhin@virahacks.com")
    return fetch(f"{EUTILS}/{endpoint}.fcgi", params=params)


def esummary_json(db: str, uid: str):
    text, url = eutils("esummary", db=db, id=uid, retmode="json")
    return json.loads(text), url


def efetch(db: str, uid: str, rettype: str, retmode: str = "text"):
    return eutils("efetch", db=db, id=uid, rettype=rettype, retmode=retmode)


def esearch_ids(db: str, term: str, retmax: int = 20):
    text, url = eutils("esearch", db=db, term=term, retmode="json", retmax=retmax)
    return json.loads(text)["esearchresult"].get("idlist", []), url
