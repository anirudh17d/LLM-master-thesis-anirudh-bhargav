import os
from pathlib import Path
from typing import Dict, Any, List

import requests

from .common import RAW_DIR, ensure_dir, write_json, utc_now_iso


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
GH_API = "https://api.github.com"
REPO = "python/cpython"
OUT_DIR = RAW_DIR / "github"


def gh_headers() -> Dict[str, str]:
	h = {"Accept": "application/vnd.github+json", "User-Agent": "research-dataset-builder/1.0"}
	if GITHUB_TOKEN:
		h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
	return h


def search_release_blockers(milestone: str) -> Dict[str, Any]:
	"""
	Use the GitHub search API to find issues with label release-blocker for a milestone title.
	"""
	q = f"repo:{REPO} label:release-blocker milestone:{milestone} is:issue"
	params = {"q": q, "per_page": 100}
	resp = requests.get(f"{GH_API}/search/issues", headers=gh_headers(), params=params, timeout=60)
	resp.raise_for_status()
	data = resp.json()
	return {
		"fetched_at": utc_now_iso(),
		"repository": REPO,
		"milestone": milestone,
		"total_count": data.get("total_count", 0),
		"items": data.get("items", []),
	}


def save_snapshot(obj: Dict[str, Any], milestone: str) -> Path:
	ensure_dir(OUT_DIR)
	out_path = OUT_DIR / f"release_blockers_{milestone.replace('.', '_')}.json"
	write_json(out_path, obj)
	return out_path


if __name__ == "__main__":
	for ms in ["3.13.1", "3.13.2"]:
		data = search_release_blockers(ms)
		path = save_snapshot(data, ms)
		print(str(path))


