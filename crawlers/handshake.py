import csv
import pathlib
import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

BASE = "https://joinhandshake.com/move-program/opportunities"
OUT = pathlib.Path("output/handshake_jobs.csv")


def clean_href(href: str) -> str:
    "remove accidental double 'opportunities/' segment"
    return re.sub(r"/opportunities/opportunities/", "/opportunities/", href, 1)


def visible_text(el):
    return " ".join(el.text.split()).strip()


def wait_for_fr_state(drv):
    WebDriverWait(drv, 25).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def lazy_scroll(drv):
    # 1. a small pause so the Framer bundle attaches
    time.sleep(1)
    # 2. scroll to ~2× viewport height to wake up the off-screen sections
    drv.execute_script("window.scrollBy(0, window.innerHeight * 2);")


def launch() -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )


driver = launch()
driver.get(BASE)
wait = WebDriverWait(driver, 25)

wait_for_fr_state(driver)

cards = driver.find_elements(By.CSS_SELECTOR, "a.framer-mNvbM[href*='opportunities/']")

urls, rows = [], []
for c in cards:
    href = clean_href(c.get_attribute("href"))
    title = visible_text(
        c.find_element(By.CSS_SELECTOR, ".framer-1j50trw p, .framer-x5c7hq p")
    )
    pay = visible_text(
        c.find_element(By.CSS_SELECTOR, ".framer-1wwhrvh p:nth-of-type(1)")
    )
    urls.append(href)
    rows.append(
        {
            "url": href,
            "title": title,
            "pay": pay,  # *from the card*
            "overview": "",
            "details": "",
            "who_apply": "",
        }
    )

print(f"[info] found {len(urls)} opportunity URLs")

for row in rows:
    driver.get(row["url"])
    wait_for_fr_state(driver)
    lazy_scroll(driver)

    # headings are <p> elements, not <h2>
    wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//p[normalize-space()='Program Overview' "
                "or normalize-space()='Program Details' "
                "or normalize-space()='Who Should Apply']",
            )
        )
    )

    # helper to grab full section text
    def grab(sec):
        try:
            return visible_text(driver.find_element(By.ID, sec))
        except Exception:
            return ""

    row["overview"] = grab("program-overview")
    row["details"] = grab("program-details")
    row["who_apply"] = grab("who-should-apply")

    # if card didn’t have pay (rare), fallback to Compensation block
    if not row["pay"]:
        compensation = grab("compensation")
        m = re.search(r"\$[\d,]+[^;.\n]*hr", compensation, re.I)
        if m:
            row["pay"] = m.group(0)

driver.quit()

fieldnames = rows[0].keys()
with open(OUT, "w") as f:
    csv.DictWriter(f, fieldnames).writeheader()
    csv.DictWriter(f, fieldnames).writerows(rows)

print(f"Wrote {len(rows)} rows ➜ {OUT}")
