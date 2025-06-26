#!/usr/bin/env python3
"""
Adds a `tag_ids` column to a jobs CSV using Gemini.

Usage
-----
python add_tags.py --in alignerr_jobs.csv --out alignerr_jobs_tagged.csv
"""

from __future__ import annotations

import config

import argparse
import csv
import json
import re
import sys
import textwrap
import time

from google import genai
from google.genai.types import Content, GenerateContentConfig, Part, ThinkingConfig


SECONDS_BETWEE_CALLS = 6


def build_system_instruction(batch_len: int) -> list[Part]:
    """Return a system instruction that locks in formatting rules."""
    rules = f"""
You are tagging job rows.

OUTPUT RULES (must be obeyed literally):
• There are EXACTLY {batch_len} jobs in this batch — produce EXACTLY {batch_len} lines.
• Each line must contain ONLY the tag ID or two IDs separated by a comma (e.g. 7,18).
• No numbering, no bullets, no extra text.
• If a job fits none of the categories, output 28 for that line.
"""
    return [Part.from_text(text=rules)]


def generate(
    system_instruction, prompt: str, model_name: str = "gemini-2.5-flash"
) -> str:
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(
            thinking_budget=0,
        ),
        response_mime_type="text/plain",
        system_instruction=system_instruction,
    )
    contents = [
        Content(
            role="user",
            parts=[Part.from_text(text=prompt)],
        ),
    ]

    chunks, text = (
        client.models.generate_content_stream(
            model=model_name, contents=contents, config=cfg
        ),
        [],
    )
    for chunk in chunks:
        if chunk.text:
            text.append(chunk.text)
    return "".join(text).strip()


##############################################################################
# Prompt pieces
##############################################################################
TAG_MENU = """\
1. Math & Stats
2. Chemistry & Materials Science
3. Physics & Astronomy
4. Biology & Life Sciences
5. Environmental Science
6. Mechanical & Industrial & Electrical Engineering
7. Computer Programming & DevOps & Cloud & Data Infrastructure
8. AI Safety & Cybersecurity
9. Game Development
10. Robotics
11. Finance, Accounting & Investment
12. Insurance & Acturial
13. Real Estate
14. Legal & Compliance
15. Supply Chain & Logistics
16. Strategy & Operations
17. Product & Project Management
18. Sales & Marketing & Customer Success
19. Data Science & Machine Learning
20. Medical & Clinical Practice
21. Creative & Digital Design
22. Social Sciences & Humanities
23. Education
24. Human Resources & Talent Management
25. Writing, Language & Localization
26. Nonprofit
27. Quality Assurance
28. None of the above categories
"""


def build_prompt(batch: list[dict[str, str]]) -> str:
    """
    Each row is a job; we don't care what the column names are.
    We simply concatenate all non-empty cells so Gemini sees the full context.
    """
    rows_txt = []
    for idx, row in enumerate(batch, 1):
        values = [str(v).strip() for v in row.values() if str(v).strip()]
        job_blob = "  ".join(values)
        rows_txt.append(f"{idx}. {job_blob}")

    instructions = f"""
        There are EXACTLY {len(batch)} jobs in this batch.
        Return EXACTLY {len(batch)} lines in the same order — each line only the tag ID(s). No numbering, no JSON.
        • If two tags apply, separate with a comma (e.g. 7,18).
        • Use 28 if none of the categories fit.
        Example (3 jobs):
        17
        7,18
        26
    """

    return f"{TAG_MENU}\n\n{instructions}\nJobs:\n" + "\n".join(rows_txt)


##############################################################################
# Parsing helper
##############################################################################
CAT_TEXT_TO_ID = {
    "none of the above categories": "28",
    "none of the above": "28",
}

_tag_line = re.compile(r"^\s*(?:\d+\s*[.)-]\s*)?(?P<ids>.+?)\s*$", re.I)


def parse_tags(raw: str, expected_rows: int) -> list[str]:
    """Return list[str] of tag IDs matching batch length."""
    # 1️⃣ JSON?
    try:
        data = json.loads(raw)
        if isinstance(data, list) and all("tags" in d for d in data):
            return [",".join(map(str, d["tags"])) if d["tags"] else "28" for d in data]
    except json.JSONDecodeError:
        pass

    # 2️⃣ Plain-text lines
    out: list[str] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        m = _tag_line.match(line)
        if not m:
            continue
        ids = m.group("ids").strip()

        low = ids.lower()
        if low in CAT_TEXT_TO_ID:
            out.append(CAT_TEXT_TO_ID[low])
            continue

        if re.fullmatch(r"\d{1,2}(,\s*\d{1,2})?$", ids):
            out.append(ids.replace(" ", ""))
            continue

    return out


##############################################################################
# Main driver
##############################################################################
def tag_jobs(inp: str, out: str, batch_size: int):
    with open(inp, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    all_tags: list[str] = []
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        prompt = build_prompt(batch)
        system_instruction = build_system_instruction(len(batch))
        print(prompt)
        print(system_instruction)

        raw = generate(system_instruction, prompt)
        tags = parse_tags(raw, len(batch))

        if len(batch) != len(tags):
            print(prompt, tags)
            raise RuntimeError(f"Need {len(batch)} tags, got {len(tags)}.")

        all_tags.extend(tags)

        time.sleep(SECONDS_BETWEE_CALLS)

    for row, tag in zip(rows, all_tags, strict=True):
        row["tag_ids"] = tag

    fieldnames = list(rows[0].keys())

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {out} ({len(rows)} rows)")


##############################################################################
# CLI
##############################################################################
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Add tag_ids column via Gemini.")
    ap.add_argument("--in", dest="inp", required=True, help="input CSV")
    ap.add_argument("--out", default="tagged.csv", help="output CSV")
    ap.add_argument("--batch", type=int, default=10, help="rows per prompt")
    args = ap.parse_args()
    try:
        tag_jobs(args.inp, args.out, args.batch)
    except KeyboardInterrupt:
        sys.exit("\nInterrupted.")
