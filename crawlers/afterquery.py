from __future__ import annotations

import csv
import re
import time
from pathlib import Path
from typing import Dict, List

import ftfy
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://experts.afterquery.com/apply"
OUTFILE = Path("output/afterquery_jobs.csv")
WAIT_SECS = 20
PAUSE_SECS = 0.6


def clean(text: str) -> str:
    return ftfy.fix_text(text)


def launch() -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )


date_pat = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}",
    re.I,
)


def parse_card_html(html: str) -> Dict[str, str]:
    """Extract Position / Category / Salary / Posted and detail URL from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    data: Dict[str, str] = {}

    data["Position"] = soup.select_one(".job-card-content h3").get_text(strip=True)

    cat_badge = soup.select_one(".flex-grow .inline-flex")
    data["Category"] = cat_badge.get_text(strip=True).title()

    salary = soup.select_one(".job-card-content div.text-blue-700")
    data["Salary Range"] = salary.get_text(strip=True) if salary else ""

    posted_raw = soup.select_one(".flex-grow p.text-xs")
    if posted_raw:
        m = date_pat.search(posted_raw.get_text(strip=True))
        data["Posted Date"] = m.group(0) if m else posted_raw.get_text(strip=True)
    else:
        data["Posted Date"] = ""

    anchor = soup.select_one("a[href^='/apply/']")
    data["Detail URL"] = (
        f"https://experts.afterquery.com{anchor['href']}" if anchor else ""
    )

    return data


def capture_section(driver, *keywords) -> str:
    kws = [kw.lower() for kw in keywords]
    head_xpath = ".//*[self::h2 or self::h3 or self::h4][{}]".format(
        " or ".join(
            f"contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{kw}')"
            for kw in kws
        )
    )
    heads = driver.find_elements(By.XPATH, head_xpath)
    if not heads:
        return ""
    snippets = []
    for sib in heads[0].find_elements(By.XPATH, "following-sibling::*"):
        if sib.tag_name.lower() in ("h2", "h3", "h4"):
            break
        if sib.text.strip():
            snippets.append(sib.text.strip())
    return "\n".join(snippets)


# ───────── scraper ────────────────────────────────────────────────────────
def scrape() -> List[Dict[str, str]]:
    drv = launch()
    wait = WebDriverWait(drv, WAIT_SECS)
    rows: List[Dict[str, str]] = []

    try:
        drv.get(URL)

        # Wait for grid, then grab the outerHTML of every card *once*.
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.card-grid")))
        card_outers = [
            c.get_attribute("outerHTML")
            for c in drv.find_elements(By.CSS_SELECTOR, "div.card-grid .job-card")
        ]

        card_info_list = [parse_card_html(html) for html in card_outers]

        # Deep dive for long-form fields
        for info in card_info_list:
            if not info["Detail URL"]:
                info.update(
                    {
                        "Job Description": "",
                        "Required Skills": "",
                        "Responsibilities": "",
                    }
                )
                rows.append(info)
                continue

            drv.execute_script("window.open(arguments[0]);", info["Detail URL"])
            drv.switch_to.window(drv.window_handles[-1])

            try:
                wait.until(EC.visibility_of_element_located((By.TAG_NAME, "h1")))
                info["Job Description"] = clean(capture_section(drv, "job description"))
                info["Required Skills"] = capture_section(
                    drv, "required skills", "skills", "qualifications"
                )
                info["Responsibilities"] = clean(capture_section(drv, "responsibil"))
            finally:
                drv.close()
                drv.switch_to.window(drv.window_handles[0])
                time.sleep(PAUSE_SECS)

            rows.append(info)

    finally:
        drv.quit()

    return rows


def save_csv(rows: List[Dict[str, str]]):
    if not rows:
        print("No rows scraped.")
        return
    with OUTFILE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} jobs → {OUTFILE.resolve()}")


if __name__ == "__main__":
    save_csv(scrape())
