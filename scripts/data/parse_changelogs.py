from pathlib import Path
from typing import Dict, Any, List
import re
import json

from bs4 import BeautifulSoup  # pip install beautifulsoup4

RAW_BASE = Path("data") / "raw" / "changelogs"
OUT_PATH = Path("data") / "processed" / "changelog_items.json"


def parse_changelog_html(html_content: str, base_url: str, series: str) -> List[Dict[str, Any]]:
	"""
	Parse a Python changelog HTML page (e.g., 3.12 or 3.13) and extract per-release sections.
	Returns a list of items with version, date, bullets, and source anchor.
	"""
	soup = BeautifulSoup(html_content, "html.parser")
	# Sections have ids like "python-3-12-2"
	sec_selector = f"section[id^='python-{series.replace('.', '-')}-']"
	items: List[Dict[str, Any]] = []
	for sec in soup.select(sec_selector):
		sec_id = sec.get("id", "")
		# Derive version like 3.12.2 from id
		m = re.search(r"python-(\d+)-(\d+)-(\d+)", sec_id)
		if not m:
			continue
		version = f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
		# Title contains date like "Python 3.12.2 (March 19, 2024)"
		title_el = sec.find(["h2", "h1"])
		title_text = title_el.get_text(" ", strip=True) if title_el else ""
		date_match = re.search(r"\((.*?)\)", title_text)
		date_text = date_match.group(1) if date_match else ""
		# Collect bullet points under the section
		bullets: List[str] = []
		for li in sec.select("li"):
			text = li.get_text(" ", strip=True)
			if text:
				bullets.append(text)
		items.append({
			"series": series,
			"version": version,
			"title": title_text,
			"date_text": date_text,
			"bullets": bullets,
			"source": f"{base_url}#{sec_id}",
		})
	return items


def load_file(path: Path) -> str:
	with open(path, "r", encoding="utf-8") as f:
		return f.read()


def main() -> None:
	series_to_url = {
		"3.12": "https://docs.python.org/3.12/whatsnew/changelog.html",
		"3.13": "https://docs.python.org/3.13/whatsnew/changelog.html",
	}
	all_items: List[Dict[str, Any]] = []
	for series, url in series_to_url.items():
		html_path = RAW_BASE / series / "changelog.html"
		if not html_path.exists():
			continue
		html = load_file(html_path)
		items = parse_changelog_html(html, url, series)
		all_items.extend(items)
	# Save
	OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
	with open(OUT_PATH, "w", encoding="utf-8") as f:
		json.dump({"count": len(all_items), "items": all_items}, f, ensure_ascii=False, indent=2)
	print(str(OUT_PATH))


if __name__ == "__main__":
	main()


