from seleniumbase import SB
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import os
import string
import re
from bs4 import BeautifulSoup
import random
from selenium.common.exceptions import TimeoutException, WebDriverException

USERNAME = "tomngo2"
PASSWORD = "cs_collab_csu"

SAVE_DIR = r"C:\Users\kaila\Downloads\acm_html"
FAILED_LOG = "failed_urls.txt"

os.makedirs(SAVE_DIR, exist_ok=True)

start_date = datetime(1990, 1, 1)
end_date = datetime(2026, 12, 31)

# -------------------------------
# Utility
# -------------------------------

def extract_doi(url):
    match = re.search(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', url, re.I)
    return match.group(0) if match else None

def doi_to_filename(doi):
    return doi.replace("/", "_") + ".html"

def log_failed(url):
    with open(FAILED_LOG, "a") as f:
        f.write(url + "\n")

# -------------------------------
# Cloudflare Handling
# -------------------------------

def wait_for_verification(sb, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        html = sb.get_page_source().lower()
        if "cf-challenge" in html or "just a moment" in html:
            print("Waiting for Cloudflare...")
            time.sleep(5)
        else:
            return True
    print("Cloudflare timeout")
    return False

def accept_cookies(sb):
    try:
        sb.wait_for_element_clickable("button:contains('Allow all cookies')", timeout=10)
        sb.click("button:contains('Allow all cookies')")
        time.sleep(2)
    except:
        pass

# -------------------------------
# Login
# -------------------------------

def login(sb):
    sb.open("https://dl.acm.org/")
    sb.wait_for_ready_state_complete()
    accept_cookies(sb)

    sb.click("a:contains('Sign In')")
    sb.click("button:contains('Sign In')")

    sb.type("input[type='username']", USERNAME)
    sb.type("input[type='password']", PASSWORD)

    sb.click("input[name='_eventId_proceed']")
    sb.wait_for_ready_state_complete()
    time.sleep(3)

# -------------------------------
# Extract Article Links
# -------------------------------

def extract_article_links(sb):
    soup = BeautifulSoup(sb.get_page_source(), "html.parser")
    links = set()

    for a in soup.select("a[href*='/doi/']"):
        href = a.get("href")
        if href:
            if href.startswith("/"):
                href = "https://dl.acm.org" + href
            links.add(href)

    return list(links)

# -------------------------------
# Save Article Page (UPDATED)
# -------------------------------

def save_article_page(sb, url):
    doi = extract_doi(url)

    if not doi:
        print(f"Skipping (no DOI): {url}")
        return

    filename = doi_to_filename(doi)
    path = os.path.join(SAVE_DIR, filename)

    if os.path.exists(path):
        print(f"Already exists: {filename}")
        return

    try:
        print(f"Opening: {url}")
        sb.open(url)

        wait_for_verification(sb)
        sb.wait_for_ready_state_complete()
        time.sleep(random.uniform(3, 6))

        # 🔥 Get page source
        html = sb.get_page_source()
        soup = BeautifulSoup(html, "html.parser")

        # 🔥 Fix relative src
        for tag in soup.find_all(src=True):
            if tag["src"].startswith("/"):
                tag["src"] = "https://dl.acm.org" + tag["src"]
            elif tag["src"].startswith("//"):
                tag["src"] = "https:" + tag["src"]

        # 🔥 Fix relative href
        for tag in soup.find_all(href=True):
            if tag["href"].startswith("/"):
                tag["href"] = "https://dl.acm.org" + tag["href"]
            elif tag["href"].startswith("//"):
                tag["href"] = "https:" + tag["href"]

        html = str(soup)

        # Save file
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Saved: {filename}")

    except Exception as e:
        print(f"Error: {url} -> {e}")
        log_failed(url)

# -------------------------------
# Wait for Results
# -------------------------------

def wait_for_results(sb, timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        if sb.is_element_visible("div.issue-item__content"):
            return True
        time.sleep(2)
    return False

# -------------------------------
# Pagination + Scraping
# -------------------------------

def paginate_and_scrape_articles(sb):

    page_number = 1

    while True:
        print(f"\n--- Page {page_number} ---")

        article_links = extract_article_links(sb)
        print(f"Found {len(article_links)} articles")

        for link in article_links:
            save_article_page(sb, link)
            time.sleep(random.uniform(2, 5))

        next_selector = f"a[aria-label='Go to page {page_number + 1}']"

        if sb.is_element_present(next_selector):
            time.sleep(random.uniform(8, 15))
            sb.click(next_selector)
        elif sb.is_element_present("li.pagination__btn--next > a"):
            time.sleep(random.uniform(8, 15))
            sb.click("li.pagination__btn--next > a")
        else:
            print("No more pages.")
            break

        sb.wait_for_ready_state_complete()
        wait_for_verification(sb)
        wait_for_results(sb)

        page_number += 1

# -------------------------------
# Advanced Search
# -------------------------------

def run_advanced_search(sb, letter, from_month, from_year, to_month, to_year):
    sb.open("https://dl.acm.org/")
    sb.wait_for_ready_state_complete()

    accept_cookies(sb)

    sb.click("a.quick-search__advancedHeader")

    sb.select_option_by_value("#searchArea1", "ContribAuthor")
    sb.type("#text1", letter)

    sb.click("#customRange")

    sb.select_option_by_value("#fromMonth", str(from_month))
    sb.select_option_by_value("#fromYear", str(from_year))
    sb.select_option_by_value("#toMonth", str(to_month))
    sb.select_option_by_value("#toYear", str(to_year))

    sb.click("#advanced-search-btn")

    wait_for_verification(sb)
    wait_for_results(sb)

# -------------------------------
# MAIN
# -------------------------------

with SB(uc=True, headless=True) as sb:

    login(sb)

    for letter in string.ascii_uppercase:

        current = start_date

        while current <= end_date:

            from_month = current.month
            from_year = current.year

            next_month = current + relativedelta(months=1)
            last_day = next_month - relativedelta(days=1)

            to_month = last_day.month
            to_year = last_day.year

            print(f"\n=== {letter} | {from_year}-{from_month} ===")

            run_advanced_search(
                sb,
                letter,
                from_month,
                from_year,
                to_month,
                to_year
            )

            time.sleep(random.uniform(8, 15))

            paginate_and_scrape_articles(sb)

            current = next_month
            time.sleep(random.uniform(5, 10))

print("Done.")