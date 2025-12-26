import argparse
import itertools
from pathlib import Path
from typing import List

from .common import fetch_url, save_with_metadata, RAW_DIR, ensure_dir


BASE_PEP_URL = "https://peps.python.org"
OUT_DIR = RAW_DIR / "peps"


def pep_url(pep_id: int) -> str:
	return f"{BASE_PEP_URL}/pep-{pep_id:04d}/"


def collect_peps(pep_ids: List[int]) -> List[Path]:
	ensure_dir(OUT_DIR)
	saved: List[Path] = []
	for pid in pep_ids:
		url = pep_url(pid)
		resp = fetch_url(url)
		raw_path = OUT_DIR / f"pep-{pid:04d}.html"
		meta_path = raw_path.with_suffix(".meta.json")
		save_with_metadata(raw_path, meta_path, url, resp.content, extra_meta={"content_type": resp.headers.get("Content-Type", "")})
		saved.append(raw_path)
	return saved


def main():
	parser = argparse.ArgumentParser(description="Cache PEP pages to data/raw/peps")
	parser.add_argument("--pep", type=int, action="append", help="PEP number (can be repeated)", default=[])
	args = parser.parse_args()
	pep_ids = args.pep or []
	if not pep_ids:
		# Fallback: cache index and a small seed set often relevant in recent cycles
		index = fetch_url(BASE_PEP_URL + "/")
		index_path = OUT_DIR / "index.html"
		save_with_metadata(index_path, index_path.with_suffix(".meta.json"), BASE_PEP_URL + "/", index.content, extra_meta={"content_type": index.headers.get("Content-Type", "")})
		pep_ids = [703, 719, 723, 727, 738, 739]  # seed; adjustable later
	collect_peps(pep_ids)


if __name__ == "__main__":
	main()


