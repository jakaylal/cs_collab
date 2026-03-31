from seleniumbase import SB
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import os
import string
import re
from bs4 import BeautifulSoup
import random

USERNAME = "tomngo2"
PASSWORD = "cs_collab_csu"

SAVE_DIR = r"C:\Users\kaila\Downloads\acm_html"
os.makedirs(SAVE_DIR, exist_ok=True)

start_date = datetime(1990, 1, 1)
end_date = datetime(2026, 3, 31)

#Cloudflare Verification
def wait_for_verification(sb, timeout=60):
    start = time.time()

    while time.time() - start < timeout:
        html = sb.get_page_source().lower()

        if "cf-challenge" in html or "just a moment" in html:
            print("Waiting for Cloudflare...")
            time.sleep(5)
        else:
            print("Verification passed")
            return True

    print("Verification wait timeout")
    return False

#Accept Cookies
def accept_cookies(sb):
    try:
        sb.wait_for_element_clickable("button:contains('Allow all cookies')", timeout=60)
        sb.click("button:contains('Allow all cookies')")
        time.sleep(2)
    except:
        pass


def wait_for_results(sb, timeout=60):
    try:
        sb.wait_for_element_visible("div.issue-item__content", timeout=timeout)
        return True
    except:
        pass

    try:
        sb.wait_for_element_visible("div.issue-item", timeout=10)
        return True
    except:
        pass

    try:
        sb.wait_for_element_visible("li.search__item", timeout=10)
        return True
    except:
        pass

    print("No known results found.")
    return False
    
def get_last_progress():
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".html")]

    if not files:
        return None

    progress = []

    pattern = re.compile(
        r"acm_([A-Z])_(\d+)_(\d+)_to_(\d+)_(\d+)_page_(\d+)\.html"
    )

    for f in files:
        match = pattern.match(f)
        if match:
            letter, from_year, from_month, to_year, to_month, page = match.groups()
            progress.append((
                letter,
                int(from_year),
                int(from_month),
                int(page)
            ))

    if not progress:
        return None


    progress.sort()

    return progress[-1]  

def save_html(sb, filename):

    html = sb.get_page_source()

    # Don't save blank pages
    if len(html.strip()) < 5000:
        print("Not saving.")
        return

    if "cf-challenge" in html.lower():
        print("Cloudflare detected, not saving.")
        return
    
    sb.wait_for_ready_state_complete()
    sb.sleep(2)

    
    #html = sb.get_page_source()

    #Parse with BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    
    for tag in soup.find_all("a", href=True):
        if tag["href"].startswith("/"):
            tag["href"] = "https://dl.acm.org" + tag["href"]


    

    
    path = os.path.join(SAVE_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"Saved: {filename}")

    


def paginate_and_save(sb, letter, from_year, from_month, to_year, to_month):

    page_number = 1

    while True:

        filename = f"acm_{letter}_{from_year}_{from_month}_to_{to_year}_{to_month}_page_{page_number}.html"
        path = os.path.join(SAVE_DIR, filename)

        
        if os.path.exists(path):
            print(f"Skipping existing file: {filename}")
        else:
            if ensure_results_loaded(sb):
                save_html(sb, filename)
            else:
                print("Page failed to load.")
                break

        next_selector = f"a[aria-label='Go to page {page_number + 1}']"

        if sb.is_element_present(next_selector):
            sb.click(next_selector)
        elif sb.is_element_present("li.pagination__btn--next > a"):
            sb.click("li.pagination__btn--next > a")
            time.sleep(random.uniform(2, 5))
        else:
            print("No more pages.")
            break

        sb.wait_for_ready_state_complete()
        wait_for_results(sb)
        time.sleep(2)
        if not ensure_results_loaded(sb):
            print("Stopping pagination due to load failure.")
            break

        page_number += 1


def results_page_loaded(sb):
    html = sb.get_page_source().lower()

    #If blank
    if len(html.strip()) < 1000:
        return False

    #If results container missing
    if "issue-item__content" not in html:
        return False

    return True

def ensure_results_loaded(sb, retries=4):
    attempt = 0
    while attempt < retries:
        sb.wait_for_ready_state_complete()
        sb.sleep(2)

        if results_page_loaded(sb):
            return True

        print(f"Results blank — reloading page (attempt {attempt+1})")
        current_url = sb.get_current_url()

        try:
            sb.open(current_url)
        except Exception:
            sb.refresh()

        sb.sleep(4)
        attempt += 1

    print("Failed to properly load results page.")
    return False


def login(sb):
    sb.open("https://dl.acm.org/")
    sb.wait_for_ready_state_complete()

    accept_cookies(sb)

    sb.wait_for_element_clickable("a:contains('Sign In')", timeout=40)
    sb.click("a:contains('Sign In')")

    sb.wait_for_element_clickable("button:contains('Sign In')", timeout=40)
    sb.click("button:contains('Sign In')")

    sb.wait_for_element("input[type='username']", timeout=5)
    sb.type("input[type='username']", USERNAME)
    sb.type("input[type='password']", PASSWORD)

    sb.click("input[name='_eventId_proceed']")
    sb.wait_for_ready_state_complete()
    sb.sleep(1)

    


def run_advanced_search(sb, letter, from_month, from_year, to_month, to_year):
    sb.open("https://dl.acm.org/")
    sb.wait_for_ready_state_complete()

    sb.wait_for_element_clickable("a.quick-search__advancedHeader", timeout=10)
    sb.click("a.quick-search__advancedHeader")

    sb.wait_for_element_visible("#searchArea1", timeout=30)

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
    ensure_results_loaded(sb)
    if not wait_for_verification(sb):
        print("Retrying search due to verification failure...")
        sb.refresh()
        wait_for_verification(sb)



def set_page_size_2000(sb):
    current_url = sb.get_current_url()

    if "pageSize=" not in current_url:
        if "?" in current_url:
            new_url = current_url + "&pageSize=2000"
        else:
            new_url = current_url + "?pageSize=2000"
    else:
        new_url = re.sub(r"pageSize=\d+", "pageSize=2000", current_url)

    sb.open(new_url)
    sb.wait_for_ready_state_complete()
    wait_for_results(sb)
    sb.sleep(2)
    
with SB(uc=True, headless=True, incognito=True) as sb:

    login(sb)

last_progress = get_last_progress()

resume_letter = None
resume_year = None
resume_month = None

if last_progress:
    resume_letter, resume_year, resume_month, _ = last_progress
    print(f"Resuming from {resume_letter} {resume_year}-{resume_month}")


for letter in string.ascii_uppercase:

    if resume_letter and letter < resume_letter:
        continue  #Skip completed letters

    with SB(uc=True, headless=True) as sb:
        login(sb)
        sb.driver.command_executor.set_timeout(600)

        current = start_date

        while current <= end_date:

            from_month = current.month
            from_year = current.year

            #Skip completed months
            if (resume_letter == letter and
                (from_year < resume_year or
                 (from_year == resume_year and from_month < resume_month))):
                current += relativedelta(months=1)
                continue

            next_month = current + relativedelta(months=1)
            last_day = next_month - relativedelta(days=1)
            

            to_month = last_day.month
            to_year = last_day.year
            time.sleep(random.uniform(4, 8))

            run_advanced_search(
                sb,
                letter,
                from_month,
                from_year,
                to_month,
                to_year
            )

            set_page_size_2000(sb)

            paginate_and_save(
                sb,
                letter,
                from_year,
                from_month,
                to_year,
                to_month
            )

            current = next_month
            time.sleep(2)

    

print("All searches completed")



