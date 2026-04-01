from seleniumbase import SB
import pandas as pd
import time
import os
import re
import random
import csv
from bs4 import BeautifulSoup

USERNAME = "tomngo2"
PASSWORD = "cs_collab_csu"

CSV_FILE = r"C:\Users\kaila\Downloads\article_list_260322.csv"
SAVE_DIR = r"C:\Users\kaila\Downloads\unique_articles_html"
FAILED_LOG = "failed_urls.txt"
OUTPUT_CSV = "downloaded_articles.csv"

os.makedirs(SAVE_DIR, exist_ok=True)

# -------------------------------
# Utility
# -------------------------------

def extract_doi(url):
    match = re.search(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', url, re.I)
    return match.group(0) if match else None

def clean_text(text):
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    text = re.sub(r'\s+', '_', text.strip())
    return text[:150]

def log_failed(url):
    with open(FAILED_LOG, "a") as f:
        f.write(url + "\n")

# -------------------------------
# 🔥 LOAD DOWNLOADED DOIs FROM CSV (NOT FILENAMES)
# -------------------------------

def get_downloaded_dois():
    if not os.path.exists(OUTPUT_CSV):
        return set()

    df = pd.read_csv(OUTPUT_CSV)
    return set(df["doi"].dropna().tolist())

# -------------------------------
# Extract Title
# -------------------------------

def extract_title(soup):
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)

    return None

# -------------------------------
# Cloudflare + Cookies
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
# LOGIN
# -------------------------------

def login(sb):
    sb.open("https://dl.acm.org/")
    sb.sleep(3)

    wait_for_verification(sb)
    accept_cookies(sb)

    sb.wait_for_element_clickable("a:contains('Sign In')", timeout=30)
    sb.click("a:contains('Sign In')")

    sb.wait_for_element_clickable("button:contains('Sign In')", timeout=30)
    sb.click("button:contains('Sign In')")

    sb.wait_for_element("input[type='username']", timeout=10)
    sb.type("input[type='username']", USERNAME)
    sb.type("input[type='password']", PASSWORD)

    sb.click("input[name='_eventId_proceed']")
    sb.sleep(5)

    wait_for_verification(sb)

# -------------------------------
# Save Rendered HTML (TITLE-BASED)
# -------------------------------

def save_rendered_html(sb):
    sb.wait_for_ready_state_complete()
    time.sleep(2)

    sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    sb.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)

    html = sb.get_page_source()
    soup = BeautifulSoup(html, "html.parser")

    title = extract_title(soup)
    current_url = sb.get_current_url()
    doi = extract_doi(current_url)

    if not title:
        return None, soup, doi

    filename_base = clean_text(title)
    filepath = os.path.join(SAVE_DIR, filename_base + ".html")

    # Fix src
    for tag in soup.find_all(src=True):
        src = tag["src"]
        if src.startswith("/"):
            tag["src"] = "https://dl.acm.org" + src
        elif src.startswith("//"):
            tag["src"] = "https:" + src

    # Fix href
    for tag in soup.find_all(href=True):
        href = tag["href"]
        if href.startswith("/"):
            tag["href"] = "https://dl.acm.org" + href
        elif href.startswith("//"):
            tag["href"] = "https:" + href

    return filepath, soup, doi

# -------------------------------
# Filter Remaining URLs
# -------------------------------

def build_remaining_dataframe(df, downloaded_dois):
    remaining_rows = []

    for _, row in df.iterrows():
        url = row["URL"]
        doi = extract_doi(url)

        if doi and doi in downloaded_dois:
            continue

        remaining_rows.append(row)

    return pd.DataFrame(remaining_rows)

# -------------------------------
# MAIN
# -------------------------------

df = pd.read_csv(CSV_FILE)

downloaded_dois = get_downloaded_dois()
print(f"Found {len(downloaded_dois)} already downloaded articles (via CSV)")

df_remaining = build_remaining_dataframe(df, downloaded_dois)
print(f"Remaining URLs to process: {len(df_remaining)}")

# CSV logging
csv_exists = os.path.exists(OUTPUT_CSV)
csv_file = open(OUTPUT_CSV, "a", newline="", encoding="utf-8")
csv_writer = csv.writer(csv_file)

if not csv_exists:
    csv_writer.writerow(["doi", "url", "filename"])

with SB(uc=True, headless=True) as sb:

    login(sb)

    for index, row in df_remaining.iterrows():
        url = row["URL"]

        try:
            print(f"\nProcessing: {url}")

            sb.open(url)

            wait_for_verification(sb)
            accept_cookies(sb)

            filepath, soup, doi = save_rendered_html(sb)

            if not filepath or not doi:
                log_failed(url)
                continue

            # Prevent duplicate titles overwriting
            if os.path.exists(filepath):
                filepath = filepath.replace(".html", f"_{random.randint(1000,9999)}.html")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(str(soup))

            print(f"Saved: {filepath}")

            # ✅ track DOI in CSV (THIS is your resume system)
            csv_writer.writerow([doi, url, os.path.basename(filepath)])
            csv_file.flush()

            downloaded_dois.add(doi)

            time.sleep(random.uniform(2, 5))

        except Exception as e:
            print(f"Failed: {url} -> {e}")
            log_failed(url)

csv_file.close()

print("Done.")