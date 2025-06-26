import csv
import html
import json
import re
import unicodedata

import requests
from bs4 import BeautifulSoup

SESSION = requests.Session()
SESSION.headers.update({"user-agent": "Mozilla/5.0"})


ALL_JOBS_URL = "https://boards-api.greenhouse.io/v1/boards/agency/departments"
OUT_FILE = "output/invisible_jobs.csv"


SPACE_RE = re.compile(r"\s+")


def clean(txt: str) -> str:
    txt = html.unescape(txt)  # &#8211; → –
    txt = unicodedata.normalize("NFKC", txt)  # ﬂ → fl  etc.
    txt = SPACE_RE.sub(" ", txt).strip()
    return txt


def parse_sections(html_doc: str) -> dict:
    soup = BeautifulSoup(html_doc, "html.parser")
    main = soup.select_one("#content") or soup
    sections, current = {}, "__description"
    sections[current] = []

    for node in main.descendants:
        if node.name and node.name.lower() in {"h1", "h2", "h3", "h4", "strong", "b"}:
            head = clean(node.get_text())
            if len(head) > 2:
                current = head.lower()
                sections.setdefault(current, [])
            continue
        if node.name in {"p", "li"} and node.get_text(strip=True):
            sections[current].append(clean(node.get_text(" ")))

    return {k: " ".join(v) for k, v in sections.items() if v}


def all_jobs():
    depts = SESSION.get(ALL_JOBS_URL, timeout=20).json()["departments"]
    jobs = []
    for d in depts:
        for job in d["jobs"]:
            jobs.append(job)
    return jobs


def run(csv_path: str):
    rows = []
    for j in all_jobs():
        details = {}
        url = j["absolute_url"]
        html = SESSION.get(url, timeout=30).text
        details = parse_sections(html)
        row = {
            "title": j["title"],
            "location": j["location"]["name"],
            "first_published": j.get("first_published"),
            "updated_at": j.get("updated_at"),
            "url": url,
            "description_raw": json.dumps(details, ensure_ascii=False),
        }
        rows.append(row)

    fieldnames = rows[0].keys()
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames).writeheader()
        csv.DictWriter(f, fieldnames).writerows(rows)

    print(f"Wrote {len(rows)} rows to {csv_path}")


if __name__ == "__main__":
    run(OUT_FILE)
