import os
import time
from pathlib import Path
from typing import Dict, Any, List
import re

import requests

from .common import RAW_DIR, ensure_dir, write_json, utc_now_iso


NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
OUT_DIR = RAW_DIR / "cves"


def _headers() -> Dict[str, str]:
	h = {"User-Agent": "research-dataset-builder/1.0"}
	api_key = os.getenv("NVD_API_KEY")
	if api_key:
		h["apiKey"] = api_key
	return h


def _with_utc_z(dt_str: str) -> str:
	"""
	Normalize to ISO8601 Zulu format if no offset provided.
	Accepts inputs that already include 'Z' or an offset like +00:00.
	"""
	if dt_str.endswith("Z"):
		return dt_str
	if re.search(r"[+-]\d{2}:\d{2}$", dt_str):
		return dt_str
	return f"{dt_str}Z"


def fetch_all(keyword: str = "CPython", start: str = "2024-01-01T00:00:00.000", end: str = "2025-12-31T23:59:59.999") -> Dict[str, Any]:
	"""
	Fetch CVEs from NVD using keyword search bounded by publication dates.
	"""
	results: List[Dict[str, Any]] = []
	start_index = 0
	page_size = 200
	while True:
		params = {
			"keywordSearch": keyword,
			"pubStartDate": _with_utc_z(start),
			"pubEndDate": _with_utc_z(end),
			"startIndex": start_index,
			"resultsPerPage": page_size,
		}
		resp = requests.get(NVD_API, headers=_headers(), params=params, timeout=60)
		resp.raise_for_status()
		data = resp.json()
		page_items = data.get("vulnerabilities", [])
		results.extend(page_items)
		total = int(data.get("totalResults", len(results)))
		start_index += len(page_items)
		if start_index >= total or not page_items:
			break
		time.sleep(0.6)
	return {
		"fetched_at": utc_now_iso(),
		"keyword": keyword,
		"pubStartDate": _with_utc_z(start),
		"pubEndDate": _with_utc_z(end),
		"count": len(results),
		"vulnerabilities": results,
	}


def save_snapshot(obj: Dict[str, Any], filename: str = "nvd_cpython_2024_2025.json") -> Path:
	ensure_dir(OUT_DIR)
	out_path = OUT_DIR / filename
	write_json(out_path, obj)
	return out_path


if __name__ == "__main__":
	data = fetch_all()
	path = save_snapshot(data)
	print(str(path))


