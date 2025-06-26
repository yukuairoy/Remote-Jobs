import csv

import requests

API = "https://boards-api.greenhouse.io/v1/boards/alignerr/jobs?content=true"
OUT = "output/alignerr_jobs.csv"


def parse_job(job):
    body_html = job.get("content", "")

    return {
        "id": job["id"],
        "title": job["title"],
        "location": job["location"]["name"],
        "first_published": job["first_published"],
        "updated_at": job["updated_at"],
        "category": job["departments"][0]["name"] if job["departments"] else "",
        "absolute_url": job["absolute_url"],
        "description_raw": body_html,
    }


resp = requests.get(API, timeout=30)
resp.raise_for_status()

rows = [parse_job(j) for j in resp.json()["jobs"]]
fieldnames = rows[0].keys()
with open(OUT, "w", newline="", encoding="utf-8") as f:
    csv.DictWriter(f, fieldnames).writeheader()
    csv.DictWriter(f, fieldnames).writerows(rows)

print(f"Wrote {len(rows)} rows ➜ {OUT}")
