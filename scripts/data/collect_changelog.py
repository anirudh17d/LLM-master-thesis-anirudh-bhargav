import re
from pathlib import Path
from typing import List

from .common import fetch_url, save_with_metadata, RAW_DIR, ensure_dir


BASE_URLS = [
	"https://docs.python.org/3.12/whatsnew/changelog.html",
	"https://docs.python.org/3.13/whatsnew/changelog.html",
]


def target_paths_for(url: str) -> Path:
	parts = url.split("/")
	version = parts[3] if len(parts) > 3 else "unknown"
	out_dir = RAW_DIR / "changelogs" / version
	ensure_dir(out_dir)
	filename = "changelog.html"
	return out_dir / filename


def collect() -> List[Path]:
	saved: List[Path] = []
	for url in BASE_URLS:
		resp = fetch_url(url)
		raw_path = target_paths_for(url)
		meta_path = raw_path.with_suffix(".meta.json")
		save_with_metadata(raw_path, meta_path, url, resp.content, extra_meta={"content_type": resp.headers.get("Content-Type", "")})
		saved.append(raw_path)
	return saved


if __name__ == "__main__":
	paths = collect()
	for p in paths:
		print(str(p))


