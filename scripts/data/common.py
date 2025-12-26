import os
import json
import time
import datetime as dt
from pathlib import Path
from typing import Dict, Any, Optional

import requests


DEFAULT_UA = "research-dataset-builder/1.0 (+https://example.org)"
RAW_DIR = Path("data") / "raw"


def ensure_dir(path: Path) -> None:
	"""
	Ensure a directory exists.
	"""
	path.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
	return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def fetch_url(url: str, headers: Optional[Dict[str, str]] = None, retry: int = 2, sleep_seconds: float = 1.0) -> requests.Response:
	"""
	Fetch a URL with a simple retry. Caller is responsible for response.content handling.
	"""
	h = {"User-Agent": DEFAULT_UA}
	if headers:
		h.update(headers)
	last_exc: Optional[Exception] = None
	for attempt in range(retry + 1):
		try:
			resp = requests.get(url, headers=h, timeout=60)
			resp.raise_for_status()
			return resp
		except Exception as exc:
			last_exc = exc
			if attempt < retry:
				time.sleep(sleep_seconds)
			else:
				raise
	raise last_exc  # pragma: no cover


def write_raw_blob(path: Path, blob: bytes) -> None:
	ensure_dir(path.parent)
	with open(path, "wb") as f:
		f.write(blob)


def write_json(path: Path, obj: Any) -> None:
	ensure_dir(path.parent)
	with open(path, "w", encoding="utf-8") as f:
		json.dump(obj, f, ensure_ascii=False, indent=2)


def save_with_metadata(raw_path: Path, meta_path: Path, source_url: str, content: bytes, extra_meta: Optional[Dict[str, Any]] = None) -> None:
	"""
	Save raw content and sidecar metadata JSON with fetch timestamp and source URL.
	"""
	write_raw_blob(raw_path, content)
	meta: Dict[str, Any] = {
		"source": source_url,
		"fetched_at": utc_now_iso(),
		"size_bytes": len(content),
	}
	if extra_meta:
		meta.update(extra_meta)
	write_json(meta_path, meta)


