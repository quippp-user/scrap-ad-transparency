from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import List, Tuple, Optional


NOISE_EXACT = {
    "sponsored",
    "ad",
    "ads",
    "litta.co.uk",
}

NOISE_REGEXES = [
    re.compile(r"^a\s+bark\.com$", re.I),
    re.compile(r"^\(?\d+[a-z]?\)?\s*bark\.com$", re.I),
    re.compile(r"^rating\s+for\s+.+$", re.I),
]

URL_REGEX = re.compile(r"(https?://|www\.)", re.I)

def normalize_line(line: str) -> str:
    line = line.strip()
    line = line.replace("\\", " ")
    line = re.sub(r"\s+", " ", line)
    line = re.sub(r"^[^A-Za-z0-9<]+", "", line)
    return line.strip()

def is_noise(line: str) -> bool:
    l = line.strip().lower()
    if not l:
        return True
    if l in NOISE_EXACT:
        return True
    for rx in NOISE_REGEXES:
        if rx.match(line.strip()):
            return True
    return False

def find_url_index(lines: List[str]) -> Optional[int]:
    for i, ln in enumerate(lines):
        if URL_REGEX.search(ln) or ".com/" in ln.lower() or ".co.uk" in ln.lower():
            return i
    return None

def looks_like_description(line: str) -> bool:
    l = line.strip()
    if any(ch in l for ch in [".", "?", "!"]):
        return True

    starts = ("find ", "get ", "compare ", "request ", "save ", "thousands ", "need ")
    if l.lower().startswith(starts):
        return True

    words = l.split()
    if len(words) >= 7 and re.search(r"[a-z]", l) and re.search(r"[A-Z]", l):
        return True

    return False

def is_headline_candidate(line: str) -> bool:
    l = line.strip()
    if not l:
        return False
    if looks_like_description(l):
        return False
    if len(l) > 90:
        return False
    if "www." in l.lower() or "http" in l.lower():
        return False
    if re.search(r"[£$€]", l):
        return False
    if re.search(r"\b(view|prices?|/hr|off)\b", l, re.I):
        return False
    return True

def join_clean(parts: List[str]) -> str:
    txt = " ".join(p.strip() for p in parts if p.strip())
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def extract_headline_description(text: str) -> Tuple[str, str]:
    raw_lines = [normalize_line(x) for x in text.splitlines()]
    lines = [ln for ln in raw_lines if ln and not is_noise(ln)]

    if not lines:
        return "", ""

    url_i = find_url_index(lines)
    start = (url_i + 1) if url_i is not None else 0

    headline_lines: List[str] = []
    i = start

    if i < len(lines):
        headline_lines.append(lines[i])
        i += 1

    if i < len(lines):
        next_line = lines[i]
        if not looks_like_description(next_line) and not next_line.lower().startswith("rating for "):
            headline_lines.append(next_line)
            i += 1

    if not headline_lines and start < len(lines):
        headline_lines = [lines[start]]
        i = start + 1

    desc_lines: List[str] = []
    for ln in lines[i:]:
        if ln.lower().startswith("rating for "):
            break
        # Drop obvious rating-number garbage lines (OCR varies)
        if re.search(r"\(\d{1,3}(,\d{3})*\)$", ln) and "rating" in " ".join(lines).lower():
            # e.g. "(2,439)" sitting near rating lines
            continue
        desc_lines.append(ln)

    headline = join_clean(headline_lines)
    description = join_clean(desc_lines)

    return headline, description


def main() -> None:
    in_dir = Path("/Users/faiyaz/Code/quippp/app-image-ocr/src/clear/text")
    out_path = Path("/Users/faiyaz/Code/ads_output.csv")

    if not in_dir.exists() or not in_dir.is_dir():
        raise SystemExit(f"Input directory not found: {in_dir}")

    txt_files = sorted(in_dir.glob("*.txt"))
    if not txt_files:
        raise SystemExit(f"No .txt files found in: {in_dir}")

    rows = []
    for fp in txt_files:
        text = fp.read_text(errors="ignore")
        h, d = extract_headline_description(text)
        rows.append({
            "file": fp.name,
            "headline": h,
            "description": d,
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "headline", "description"])
        w.writeheader()
        w.writerows(rows)

    print(f"✅ Done. Wrote {len(rows)} rows to: {out_path}")


if __name__ == "__main__":
    main()
