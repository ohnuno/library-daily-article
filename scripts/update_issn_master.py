"""
月次バッチ: T&F SSH タイトルリスト PDF から ISSN マスタを更新する

実行方法:
    python scripts/update_issn_master.py
"""

import io
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pdfplumber
import requests

JST = timezone(timedelta(hours=9))
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

TF_PDF_URL = "https://files.taylorandfrancis.com/ssh-title-list.pdf"
HEADERS = {
    "User-Agent": "tufs-daily-article/1.0 (ISSN updater; https://github.com/ohnuno/tufs-daily-article-dev)"
}
ISSN_PATTERN = re.compile(r"\b(\d{4}-\d{3}[\dXx])\b")


def download_pdf(url: str) -> bytes:
    print(f"  Downloading: {url}")
    resp = requests.get(url, headers=HEADERS, timeout=60, stream=True)
    resp.raise_for_status()
    return resp.content


def extract_issns_from_pdf(pdf_bytes: bytes) -> list[str]:
    issns: set[str] = set()
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for m in ISSN_PATTERN.finditer(text):
                issns.add(m.group(1).upper())
    return sorted(issns)


def main():
    now = datetime.now(JST)
    today_str = now.strftime("%Y-%m-%d")

    master_path = DATA_DIR / "issn-master.json"
    if master_path.exists():
        with open(master_path, encoding="utf-8") as f:
            master = json.load(f)
    else:
        master = {"sources": {}}

    # ── T&F SSH ──────────────────────────────────────────────
    print("[1] Downloading T&F SSH title list PDF...")
    try:
        pdf_bytes = download_pdf(TF_PDF_URL)
    except Exception as e:
        print(f"[ERROR] Failed to download T&F PDF: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  Downloaded: {len(pdf_bytes) // 1024} KB")

    print("[2] Extracting ISSNs from PDF...")
    issns = extract_issns_from_pdf(pdf_bytes)

    if not issns:
        print("[ERROR] No ISSNs found in PDF. Check PDF format.", file=sys.stderr)
        sys.exit(1)

    print(f"  Found {len(issns)} ISSNs.")

    # ── 更新 ──────────────────────────────────────────────────
    master["updated_at"] = today_str
    master.setdefault("sources", {})
    master["sources"]["taylor-francis-ssh"] = {
        "title_list_url": TF_PDF_URL,
        "issns": issns,
    }

    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=2)

    print(f"[OK] issn-master.json updated ({len(issns)} ISSNs for T&F SSH).")


if __name__ == "__main__":
    main()
