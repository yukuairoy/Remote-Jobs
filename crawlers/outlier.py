import csv
import re
import time
import uuid
from pathlib import Path

import requests
from bs4 import BeautifulSoup

CSV_PATH = Path("output/outlier_jobs.csv")
BASE = "https://app.outlier.ai/internal/experts/job-board"
HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0 (compatible; outlier-scraper/1.1)",
}
BODY = {"podsToExclude": []}
PAY_RE = re.compile(
    r"\$\d[\d,]*(?:\s*-\s*\$\d[\d,]*)?\s*(?:per|/)\s*hour",
    flags=re.I,
)
REQ_HDR_RE = re.compile(r"^Required\s+expertise", re.I)
PAY_HDR_RE = re.compile(r"^Payment", re.I)


def api_list(page_id: str) -> list[dict]:
    url = f"{BASE}/jobs?pageLoadId={page_id}"
    resp = requests.post(url, headers=HEADERS, json=BODY, timeout=20)
    resp.raise_for_status()
    return resp.json().get("jobs", [])


def api_detail(job_id: int, page_id: str, anon: str) -> dict:
    url = f"{BASE}/jobs/{job_id}?anonymousId={anon}&pageLoadId={page_id}"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _clean_html_to_text(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def parse_detail(content_html: str) -> tuple[str, str, str]:
    """
    -> (description, requirements, payment)
    description  : text before 'Required expertise...' header
    requirements : '; ' joined list items under that header
    payment      : first '$...' snippet under 'Payment'
    """
    soup = BeautifulSoup(content_html, "html.parser")
    text_blocks: list[str] = []
    req_items: list[str] = []
    payment_snip: str = ""

    # Walk over top-level tags
    in_desc = True
    for tag in soup.children:
        if getattr(tag, "get_text", None) is None:
            continue
        txt = tag.get_text(" ", strip=True)
        if REQ_HDR_RE.match(txt):
            in_desc = False
            # collect following <ul> items
            ul = tag.find_next("ul")
            if ul:
                req_items = [li.get_text(" ", strip=True) for li in ul.find_all("li")]
        elif PAY_HDR_RE.match(txt):
            # grab first pay snippet in that section
            payment_snip = PAY_RE.search(tag.parent.get_text(" ", strip=True) or "")
            payment_snip = payment_snip.group(0) if payment_snip else ""
        elif in_desc:
            # description paragraphs until we hit requirements header
            text_blocks.append(txt)

        # Payment paragraph may appear later
        if not payment_snip and PAY_HDR_RE.search(txt):
            payment_snip = PAY_RE.search(tag.get_text(" ", strip=True) or "") or ""
            payment_snip = payment_snip.group(0) if payment_snip else ""

    description = " ".join(text_blocks)
    requirements = "; ".join(req_items)
    return description, requirements, payment_snip


def main() -> None:
    page_id = str(uuid.uuid4())
    anon_id = str(uuid.uuid4())
    jobs_raw = api_list(page_id)
    rows = []

    for j in jobs_raw:
        job_id = j["id"]
        detail = api_detail(job_id, page_id, anon_id)

        desc, reqs, pay = parse_detail(detail.get("content", ""))

        rows.append(
            {
                "id": job_id,
                "title": detail.get("title", "").strip(),
                "location": (detail.get("location") or {}).get("name", ""),
                "description": desc,
                "requirements": reqs,
                "payment": pay or "",  # fallback if not parsed
                "url": f"https://app.outlier.ai/en/expert/opportunities/{job_id}",
            }
        )
        time.sleep(0.5)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "title",
                "location",
                "description",
                "requirements",
                "payment",
                "url",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows → {CSV_PATH.resolve()}")


if __name__ == "__main__":
    main()
