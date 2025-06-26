import csv

import ftfy
import requests

API = "https://aws.api.mercor.com/work/listings-public?search="
OUT = "output/mercor_jobs.csv"
ABS_BASE = "https://work.mercor.com/jobs/"
PAY_FMT = "${min:,.0f} - ${max:,.0f} {freq}"


def clean(text: str) -> str:
    return ftfy.fix_text(text)


def parse_job(j: dict) -> dict:
    body_md = j.get("description", "")
    body_txt = clean(body_md)
    pay_range = PAY_FMT.format(
        min=j["rateMin"], max=j["rateMax"], freq=j.get("payRateFrequency", "").lower()
    )

    return {
        "id": j["listingId"],
        "absolute_url": ABS_BASE + j["listingId"],
        "title": j["title"],
        "location": j.get("location", ""),
        "commitment": j.get("commitment", ""),
        "first_published": j.get("postedAt", ""),
        "updated_at": j.get("createdAt", ""),
        "compensation": clean(pay_range),
        "description": body_txt,
    }


resp = requests.get(API, headers={"accept": "application/json"}, timeout=30)
resp.raise_for_status()

rows = [parse_job(j) for j in resp.json()]

fieldnames = rows[0].keys()

with open(OUT, "w", newline="", encoding="utf-8") as f:
    csv.DictWriter(f, fieldnames).writeheader()
    csv.DictWriter(f, fieldnames).writerows(rows)

print(f"Wrote {len(rows)} rows ➜ {OUT}")
