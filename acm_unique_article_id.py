import os
import re
import csv
from bs4 import BeautifulSoup


HTML_FOLDER = r"C:\Users\kaila\Downloads\unique_articles_html"


OUTPUT_CSV = "acm_unique_article_id.csv"


DOI_PATTERN = re.compile(r"https://dl\.acm\.org/doi/(10\.\d{4,9}/[^\s\"<>]+)")


def extract_doi_from_html(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    
    for a_tag in soup.find_all("a", href=True):
        match = DOI_PATTERN.search(a_tag["href"])
        if match:
            return match.group(1)

    # Fallback: search entire HTML
    match = DOI_PATTERN.search(str(soup))
    if match:
        return match.group(1)

    return None


def main():
    rows = []

    # Get all HTML files
    files = [
        f for f in os.listdir(HTML_FOLDER)
        if f.endswith(".html")
    ]

    # Sort files by creation time (oldest → newest)
    files.sort(key=lambda x: os.path.getctime(os.path.join(HTML_FOLDER, x)))

    # Process files in order
    for filename in files:
        file_path = os.path.join(HTML_FOLDER, filename)

        doi = extract_doi_from_html(file_path)

        if doi:
            rows.append([filename, doi])
        else:
            print(f"DOI not found in {filename}")

    # Remove duplicates while preserving order
    seen = set()
    unique_rows = []

    for row in rows:
        doi = row[1]
        if doi not in seen:
            seen.add(doi)
            unique_rows.append(row)

    
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "doi"])
        writer.writerows(unique_rows)

    print(f"Saved {len(unique_rows)} unique records to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
