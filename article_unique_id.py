from seleniumbase import SB
import pandas as pd
import time
import os
import re
import random
from bs4 import BeautifulSoup

USERNAME = "tomngo2"
PASSWORD = "cs_collab_csu"

CSV_FILE = r"C:\Users\kaila\Downloads\article_list_260322.csv"
SAVE_DIR = r"C:\Users\kaila\Downloads\unique_articles_html"
FAILED_LOG = "failed_urls.txt"

os.makedirs(SAVE_DIR, exist_ok=True)


def extract_doi(url):
    match = re.search(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', url, re.I)
    return match.group(0) if match else None

def clean_doi(doi):
    return doi.replace("/", "_")

def log_failed(url):
    with open(FAILED_LOG, "a") as f:
        f.write(url + "\n")



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



def save_rendered_html(sb, filepath):
    sb.wait_for_ready_state_complete()
    time.sleep(2)

    # Scroll to load lazy content
    sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    sb.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)

    html = sb.get_page_source()
    soup = BeautifulSoup(html, "html.parser")

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

    # Fix inline CSS
    for tag in soup.find_all(style=True):
        tag["style"] = re.sub(
            r'url\((/.*?)\)',
            r'url(https://dl.acm.org\1)',
            tag["style"]
        )

    # Fix <style> blocks
    for style_tag in soup.find_all("style"):
        if style_tag.string:
            style_tag.string = re.sub(
                r'url\((/.*?)\)',
                r'url(https://dl.acm.org\1)',
                style_tag.string
            )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(str(soup))



df = pd.read_csv(CSV_FILE)
URL_COLUMN = "URL"

with SB(uc=True, headless=True) as sb:

    login(sb)

    for index, row in df.iterrows():
        url = row[URL_COLUMN]

        try:
            doi = extract_doi(url)

            if not doi:
                print(f"Invalid DOI: {url}")
                log_failed(url)
                continue

            clean_id = clean_doi(doi)
            filepath = os.path.join(SAVE_DIR, clean_id + ".html")

            if os.path.exists(filepath):
                print(f"Skipping: {doi}")
                continue

            print(f"Processing: {doi}")

            sb.open(url)

            wait_for_verification(sb)
            accept_cookies(sb)

            save_rendered_html(sb, filepath)

            print(f"Saved: {clean_id}.html")

            time.sleep(random.uniform(2, 5))

        except Exception as e:
            print(f"Failed: {url} -> {e}")
            log_failed(url)

print("Done.")