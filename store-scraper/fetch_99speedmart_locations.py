#!/usr/bin/env python3
"""Fetch and transform 99 Speedmart store records via the WordPress REST API
and save a formatted JSON file matching the requested schema.

By default writes `data/99_speedmart_locations.json` (formatted schema).
Use `--raw-output <path>` to also save the raw paginated dump.

Usage:
  python fetch_99speedmart_locations.py --output data/99_speedmart_locations.json
"""
import argparse
import html
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

API_ROOT = "https://99speedmart.com.my/wp-json/wp/v2/stores"
PER_PAGE = 100


def extract_place_id(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    m = re.search(r'place_id:([A-Za-z0-9_-]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'/place/([A-Za-z0-9_-]{10,})', url)
    if m:
        return m.group(1)
    return None


def extract_lat_lng(url: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    if not url:
        return None, None
    m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            return None, None
    m2 = re.search(r'([-+]?\d{1,2}\.\d+),\s*([-+]?\d{1,3}\.\d+)', url)
    if m2:
        try:
            return float(m2.group(1)), float(m2.group(2))
        except ValueError:
            return None, None
    return None, None


def phone_from_acf(acf: Dict[str, Any]) -> Optional[str]:
    for key in ("phone", "phone_number", "store_phone", "telephone"):
        v = acf.get(key)
        if v:
            return v
    return None


def clean_branch_name(title: Optional[Any], idx: Optional[int]) -> str:
    if isinstance(title, dict):
        title = title.get("rendered")
    if not title:
        return f"99 Speedmart {idx or ''}".strip()
    t = html.unescape(str(title))
    t = re.sub(r"[\u2013\u2014\u2012-]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return f"99 Speedmart {t}"


def fetch_page(session: requests.Session, page: int) -> List[Dict[str, Any]]:
    params = {"per_page": PER_PAGE, "page": page}
    resp = session.get(API_ROOT, params=params, timeout=30)
    if resp.status_code in (404, 400):
        return []
    resp.raise_for_status()
    return resp.json()


def transform_one(raw: Dict[str, Any]) -> Dict[str, Any]:
    acf = raw.get("acf") or {}
    maps = acf.get("maps") or raw.get("maps")
    place_id = raw.get("place_id") or extract_place_id(maps)
    lat, lng = extract_lat_lng(maps)
    branch = clean_branch_name(raw.get("title"), raw.get("id"))
    address = acf.get("store_address") or raw.get("address") or ""
    phone = phone_from_acf(acf)
    return {
        "store_name": "99 Speedmart",
        "branch_name": branch,
        "address": address,
        "latitude": lat,
        "longitude": lng,
        "phone": phone,
        "rating": None,
        "total_ratings": None,
        "place_id": place_id,
    }


def fetch_all_formatted(session: requests.Session) -> List[Dict[str, Any]]:
    all_records: List[Dict[str, Any]] = []
    page = 1
    while True:
        print(f"Fetching page {page}...", file=sys.stderr)
        data = fetch_page(session, page)
        if not data:
            break
        for item in data:
            all_records.append(transform_one(item))
        page += 1
        time.sleep(0.08)
    return all_records


def write_json(path: str, data: List[Dict[str, Any]]) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and transform 99 Speedmart locations")
    parser.add_argument("--output", "-o", default="data/99_speedmart_locations.json",
                        help="Formatted output JSON path (relative to script directory)")
    parser.add_argument("--raw-output", dest="raw_output", default=None,
                        help="Optional: save raw paginated dump to this path")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = args.output if os.path.isabs(args.output) else os.path.join(script_dir, args.output)
    raw_out = None
    if args.raw_output:
        raw_out = args.raw_output if os.path.isabs(args.raw_output) else os.path.join(script_dir, args.raw_output)

    session = requests.Session()
    formatted = fetch_all_formatted(session)
    print(f"Fetched {len(formatted)} stores. Writing formatted output to {out_path}", file=sys.stderr)
    write_json(out_path, formatted)

    if raw_out:
        print(f"Also writing raw paginated dump to {raw_out}", file=sys.stderr)
        page = 1
        raw_pages: List[Dict[str, Any]] = []
        while True:
            data = fetch_page(session, page)
            if not data:
                break
            raw_pages.extend(data)
            page += 1
        write_json(raw_out, raw_pages)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Fetch all 99 Speedmart store records via the WordPress REST API
and save a normalized JSON file similar to data/99_speedmart_locations.json.

Usage:
  python fetch_99speedmart_locations.py --output data/99_speedmart_locations.json
"""
import argparse
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

import requests

API_ROOT = "https://99speedmart.com.my/wp-json/wp/v2/stores"
PER_PAGE = 100


def extract_place_id(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    # common patterns: ?q=place_id:PLACEID  or /place/PLACEID
    m = re.search(r'place_id:([A-Za-z0-9_-]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'/place/([A-Za-z0-9_-]{10,})', url)
    if m:
        return m.group(1)
    # sometimes maps URL contains @lat,long - no place_id
    return None


def fetch_page(session: requests.Session, page: int) -> List[Dict[str, Any]]:
    params = {"per_page": PER_PAGE, "page": page}
    resp = session.get(API_ROOT, params=params, timeout=30)
    # WordPress may return 400 for pages beyond last page, treat as empty
    if resp.status_code in (404, 400):
        return []
    resp.raise_for_status()
    return resp.json()


def normalize_store(raw: Dict[str, Any]) -> Dict[str, Any]:
    acf = raw.get("acf") or {}
    title = raw.get("title")
    if isinstance(title, dict):
        title = title.get("rendered")
    normalized = {
        "id": raw.get("id"),
        "title": title,
        "acf": acf,
        "maps": acf.get("maps"),
        "place_id": extract_place_id(acf.get("maps")),
        "state_name": raw.get("state_name"),
        "area_name": raw.get("area_name"),
        "taxonomy_terms": raw.get("taxonomy_terms"),
    }
    return normalized


def fetch_all() -> List[Dict[str, Any]]:
    session = requests.Session()
    all_stores: List[Dict[str, Any]] = []
    page = 1
    while True:
        print(f"Fetching page {page}...", file=sys.stderr)
        data = fetch_page(session, page)
        if not data:
            break
        for item in data:
            all_stores.append(normalize_store(item))
        # Use header if available to stop early
        # X-WP-TotalPages header is common on WP REST endpoints
        # but may not always be present; fall back to empty page termination above.
        # small sleep to be polite
        page += 1
        time.sleep(0.08)
    return all_stores


def write_output(out_path: str, data: List[Dict[str, Any]]) -> None:
    dirpath = os.path.dirname(out_path)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Fetch and transform 99 Speedmart locations")
    parser.add_argument("--output", "-o", default="data/99_speedmart_locations.json",
                        help="Formatted output JSON path (relative to script directory)")
    parser.add_argument("--raw-output", dest="raw_output", default=None,
                        help="Optional: save raw paginated dump to this path")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = args.output if os.path.isabs(args.output) else os.path.join(script_dir, args.output)
    raw_out = None
    if args.raw_output:
        raw_out = args.raw_output if os.path.isabs(args.raw_output) else os.path.join(script_dir, args.raw_output)

    session = requests.Session()
    formatted = fetch_all_formatted(session)
    print(f"Fetched {len(formatted)} stores. Writing formatted output to {out_path}", file=sys.stderr)
    write_json(out_path, formatted)

    if raw_out:
        # If user requested raw dump, fetch pages raw again (or we could have stored)
        print(f"Also writing raw paginated dump to {raw_out}", file=sys.stderr)
        # Re-fetch raw pages
        page = 1
        raw_pages: List[Dict[str, Any]] = []
        while True:
            data = fetch_page(session, page)
            if not data:
                break
            raw_pages.extend(data)
            page += 1
        write_json(raw_out, raw_pages)


if __name__ == "__main__":
    main()
