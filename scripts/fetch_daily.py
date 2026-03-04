"""
日次バッチ: Wikipedia → Gemini → CrossRef → today.json

Phase 1 実装:
  ① CrossRef × T&F SSH ISSNフィルタで検索
  ④ フォールバック: 教員著作論文（ROR ID / affiliation）

実行方法:
    python scripts/fetch_daily.py
"""

import json
import os
import random
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from google import genai as google_genai

# ── 定数 ──────────────────────────────────────────────────
JST = timezone(timedelta(hours=9))
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CONTACT_EMAIL = os.environ["CONTACT_EMAIL"]
TUFS_ROR_ID = os.environ.get("TUFS_ROR_ID", "https://ror.org/03f4q9q08")

CROSSREF_BASE = "https://api.crossref.org/works"
UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
WIKIPEDIA_BASE = "https://ja.wikipedia.org/w/api.php"

HEADERS = {
    "User-Agent": (
        f"tufs-daily-article/1.0 "
        f"(https://github.com/ohnuno/tufs-daily-article-dev; mailto:{CONTACT_EMAIL})"
    )
}

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_MODEL_FALLBACK = "gemini-2.0-flash"
_gemini = google_genai.Client(api_key=GEMINI_API_KEY)


def _gemini_generate(prompt: str, retries: int = 3) -> str:
    """Gemini でテキスト生成。429 時はフォールバックモデルでリトライ"""
    import time
    models = [GEMINI_MODEL, GEMINI_MODEL_FALLBACK]
    for attempt, model in enumerate(models):
        for wait in [10, 30]:
            try:
                resp = _gemini.models.generate_content(model=model, contents=prompt)
                return resp.text.strip()
            except Exception as e:
                msg = str(e)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    if wait == 10:
                        print(f"[WARN] Gemini 429 on {model}, retrying in {wait}s...", file=sys.stderr)
                        time.sleep(wait)
                    else:
                        print(f"[WARN] Gemini 429 on {model}, switching model...", file=sys.stderr)
                        break  # 次のモデルへ
                else:
                    raise
    raise RuntimeError("All Gemini models exhausted (429)")


# ── Wikipedia ─────────────────────────────────────────────
def fetch_wikipedia_events(date: datetime) -> list[str]:
    """今日の日付ページから「できごと」セクションのテキストを取得"""
    title = f"{date.month}月{date.day}日"
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": title,
        "format": "json",
    }
    resp = requests.get(WIKIPEDIA_BASE, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    pages = resp.json()["query"]["pages"]
    page = next(iter(pages.values()))
    content = page["revisions"][0]["slots"]["main"]["*"]

    # 「== できごと ==」セクションを抽出
    match = re.search(
        r"==\s*できごと\s*==\s*(.*?)(?===\s*\w)", content, re.DOTALL
    )
    if not match:
        return []

    section = match.group(1)
    # 箇条書き行（* または ** で始まる）を抽出
    lines = re.findall(r"^\*+\s*(.+)$", section, re.MULTILINE)
    # WikiMarkup [[表示名|リンク]] → 表示名
    events = [
        re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", line).strip()
        for line in lines
    ]
    return [e for e in events if len(e) > 5]


# ── Gemini ────────────────────────────────────────────────
def generate_keywords(event_text: str) -> list[str]:
    """出来事テキストから学術英語キーワードを生成"""
    prompt = (
        "次の出来事から、学術論文検索に適した英語キーワードを3〜5語生成してください。\n"
        "固有名詞よりも概念・分野語を優先すること。\n"
        "出力はJSON配列のみ。例: [\"keyword1\", \"keyword2\", \"keyword3\"]\n\n"
        f"出来事: {event_text}"
    )
    text = _gemini_generate(prompt)
    m = re.search(r"\[.*?\]", text, re.DOTALL)
    if not m:
        raise ValueError(f"Unexpected Gemini response: {text[:100]}")
    return json.loads(m.group())


def generate_japanese_summary(abstract: str) -> str:
    """Abstract を大学生向け日本語 200 字以内に要約"""
    prompt = (
        "以下のAbstractを、大学生が読んでわかる日本語で200字以内に要約してください。\n"
        "要約のみを出力し、前置きや説明は不要です。\n\n"
        f"Abstract: {abstract}"
    )
    return _gemini_generate(prompt)


# ── CrossRef ──────────────────────────────────────────────
def search_crossref(keywords: list[str], issns: list[str], rows: int = 5) -> list[dict]:
    """CrossRef API で論文を検索。issns が空なら ISSN フィルタなし"""
    params: dict = {
        "query": " ".join(keywords),
        "rows": rows,
        "sort": "relevance",
        "mailto": CONTACT_EMAIL,
    }
    if issns:
        # URL が長すぎる場合に備え先頭 200 件に絞る
        params["filter"] = ",".join(f"issn:{issn}" for issn in issns[:200])

    resp = requests.get(CROSSREF_BASE, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()["message"]["items"]


def extract_paper_info(item: dict, db_id: str) -> dict | None:
    """CrossRef レスポンスから論文情報を抽出"""
    titles = item.get("title", [])
    if not titles:
        return None

    authors = []
    for a in item.get("author", [])[:3]:
        family = a.get("family", "")
        given_initial = a.get("given", "")[:1]
        name = f"{family}, {given_initial}." if given_initial else family
        if name.strip(", ."):
            authors.append(name)

    journal = next(iter(item.get("container-title", [])), "")
    year = None
    if "published" in item:
        parts = item["published"].get("date-parts", [[None]])[0]
        year = parts[0] if parts else None

    doi = item.get("DOI", "")
    abstract = re.sub(r"<[^>]+>", "", item.get("abstract", "")).strip()
    issn = next(iter(item.get("ISSN", [])), "")

    return {
        "title": titles[0],
        "authors": authors,
        "journal": journal,
        "issn": issn,
        "year": year,
        "doi": doi,
        "doi_url": f"https://doi.org/{doi}" if doi else "",
        "abstract_original": abstract,
        "db_id": db_id,
    }


def pick_best_paper(items: list[dict], databases: dict) -> dict | None:
    """Abstract があるものを優先して 1 件選択"""
    for item in items:
        doi = item.get("DOI", "")
        db_id = determine_db_id(doi, databases)
        info = extract_paper_info(item, db_id)
        if info and info.get("abstract_original"):
            return info
    # Abstract なしでもヒットがあれば先頭を採用
    if items:
        doi = items[0].get("DOI", "")
        db_id = determine_db_id(doi, databases)
        return extract_paper_info(items[0], db_id)
    return None


# ── Unpaywall ─────────────────────────────────────────────
def fetch_abstract_from_unpaywall(doi: str) -> str:
    """Unpaywall から Abstract を補完（失敗しても空文字を返す）"""
    if not doi:
        return ""
    try:
        url = f"{UNPAYWALL_BASE}/{doi}"
        resp = requests.get(url, params={"email": CONTACT_EMAIL}, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("abstract", "") or ""
    except Exception:
        pass
    return ""


# ── ユーティリティ ────────────────────────────────────────
def load_databases() -> dict:
    with open(DATA_DIR / "databases.json", encoding="utf-8") as f:
        return {db["id"]: db for db in json.load(f)}


def load_issn_master() -> dict:
    path = DATA_DIR / "issn-master.json"
    if not path.exists():
        return {"sources": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_issns(issn_master: dict, source_id: str) -> list[str]:
    return issn_master.get("sources", {}).get(source_id, {}).get("issns", [])


def determine_db_id(doi: str, databases: dict) -> str:
    """DOI ドメインから databases.json の id を判定"""
    for db_id, db in databases.items():
        domain = db.get("doi_domain", "")
        if domain and domain in doi:
            return db_id
    return next(iter(databases), "unknown")


# ── フォールバック④: 教員著作論文 ────────────────────────
def search_faculty_papers(issns_tf: list[str]) -> list[dict]:
    """ROR ID → affiliation 文字列の順で教員著作論文を検索"""
    issn_filter = ",".join(f"issn:{issn}" for issn in issns_tf[:200]) if issns_tf else ""

    # a. ROR ID
    params: dict = {
        "filter": f"affiliation.id:{TUFS_ROR_ID}",
        "rows": 5,
        "sort": "relevance",
        "mailto": CONTACT_EMAIL,
    }
    if issn_filter:
        params["filter"] += f",{issn_filter}"

    try:
        resp = requests.get(CROSSREF_BASE, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        items = resp.json()["message"]["items"]
        if items:
            return items
    except Exception as e:
        print(f"[WARN] ROR search failed: {e}", file=sys.stderr)

    # b. affiliation 文字列
    params2: dict = {
        "query.affiliation": "Tokyo University of Foreign Studies",
        "rows": 5,
        "sort": "relevance",
        "mailto": CONTACT_EMAIL,
    }
    if issn_filter:
        params2["filter"] = issn_filter

    try:
        resp = requests.get(CROSSREF_BASE, params=params2, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()["message"]["items"]
    except Exception as e:
        print(f"[WARN] Affiliation search failed: {e}", file=sys.stderr)

    return []


# ── メイン ────────────────────────────────────────────────
def main():
    now = datetime.now(JST)
    today_str = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%dT%H:%M:%S+09:00")

    databases = load_databases()
    issn_master = load_issn_master()
    issns_tf = get_issns(issn_master, "taylor-francis-ssh")

    # ── ステップ 1: Wikipedia ──────────────────────────────
    print("[1] Fetching Wikipedia events...")
    try:
        events = fetch_wikipedia_events(now)
    except Exception as e:
        print(f"[WARN] Wikipedia fetch failed: {e}", file=sys.stderr)
        events = []

    if not events:
        events = ["言語と文化の交差点"]  # 最終フォールバック文言
    event = random.choice(events)
    print(f"  Selected event: {event}")

    # ── ステップ 2: Gemini キーワード生成 ─────────────────
    print("[2] Generating keywords with Gemini...")
    try:
        keywords_en = generate_keywords(event)
    except Exception as e:
        print(f"[WARN] Keyword generation failed: {e}", file=sys.stderr)
        keywords_en = ["linguistics", "language", "culture", "society"]
    print(f"  Keywords: {keywords_en}")

    # ── ステップ 3: CrossRef 検索（① T&F SSH）─────────────
    flow: str | None = None
    paper_info: dict | None = None

    print("[3] Searching CrossRef (T&F SSH)...")
    try:
        items = search_crossref(keywords_en, issns_tf)
        paper_info = pick_best_paper(items, databases)
        if paper_info:
            flow = "primary"
    except Exception as e:
        print(f"[WARN] CrossRef search failed: {e}", file=sys.stderr)

    # ── ステップ 4（フォールバック④）: 教員著作論文 ───────
    if not paper_info:
        print("[4] Fallback: searching faculty papers (ROR / affiliation)...")
        try:
            fb_items = search_faculty_papers(issns_tf)
            paper_info = pick_best_paper(fb_items, databases)
            if paper_info:
                flow = "fallback-faculty"
        except Exception as e:
            print(f"[WARN] Faculty fallback failed: {e}", file=sys.stderr)

    if not paper_info:
        print("[ERROR] All searches failed. Keeping previous today.json.", file=sys.stderr)
        sys.exit(0)

    # ── ステップ 5: Abstract 補完（Unpaywall）─────────────
    if not paper_info.get("abstract_original") and paper_info.get("doi"):
        print("[5] Fetching abstract from Unpaywall...")
        abstract = fetch_abstract_from_unpaywall(paper_info["doi"])
        if abstract:
            paper_info["abstract_original"] = abstract

    # ── ステップ 6: Gemini 日本語要約 ─────────────────────
    abstract_ja = ""
    if paper_info.get("abstract_original"):
        print("[6] Generating Japanese summary with Gemini...")
        try:
            abstract_ja = generate_japanese_summary(paper_info["abstract_original"])
        except Exception as e:
            print(f"[WARN] Summary generation failed: {e}", file=sys.stderr)

    # ── ステップ 7: today.json 生成 ───────────────────────
    db_id = paper_info.get("db_id", next(iter(databases), "unknown"))
    db_meta = databases.get(db_id, {})
    keywords_ja = re.findall(r"[\u4e00-\u9fff\u30a0-\u30ff\u3040-\u309f]{2,}", event)[:5]

    result = {
        "date": today_str,
        "generated_at": generated_at,
        "flow": flow,
        "today_topic": {
            "text": event,
            "keywords_ja": keywords_ja,
            "keywords_en": keywords_en,
        },
        "paper": {
            "title": paper_info.get("title", ""),
            "authors": paper_info.get("authors", []),
            "journal": paper_info.get("journal", ""),
            "issn": paper_info.get("issn", ""),
            "year": paper_info.get("year"),
            "doi": paper_info.get("doi", ""),
            "doi_url": paper_info.get("doi_url", ""),
            "abstract_original": paper_info.get("abstract_original", ""),
            "abstract_ja": abstract_ja,
            "db_id": db_id,
        },
        "database": {
            "id": db_id,
            "name": db_meta.get("name", ""),
            "description": db_meta.get("description", ""),
            "url": db_meta.get("url", ""),
            "access_note": db_meta.get("access_note", ""),
            "ip_restricted": db_meta.get("ip_restricted", False),
        },
    }

    output_path = DATA_DIR / "today.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] today.json written: date={today_str}, flow={flow}")
    print(f"     Paper: {paper_info.get('title', 'N/A')[:70]}")


if __name__ == "__main__":
    main()
