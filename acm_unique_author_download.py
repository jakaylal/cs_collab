import os
import csv
from bs4 import BeautifulSoup


HTML_FOLDER = r"C:\Users\kaila\Downloads\unique_articles_html"


OUTPUT_CSV = "acm_unique_authors.csv"


def extract_authors(soup):
    authors = []
    seen = set()

    
    author_blocks = soup.find_all(attrs={"property": "author"})

    for block in author_blocks:
        given = block.find("span", property="givenName")
        family = block.find("span", property="familyName")

        if given and family:
            name = f"{given.get_text(strip=True)} {family.get_text(strip=True)}"

            profile_tag = block.find("a", class_="profile-link")

            author_link = ""
            if profile_tag and profile_tag.get("href"):
                href = profile_tag.get("href")
                author_link = href if href.startswith("http") else "https://dl.acm.org" + href

            author_id = author_link or name.lower()

            if author_id not in seen:
                seen.add(author_id)
                authors.append({
                    "name": name,
                    "author_link": author_link
                })

    # -----------------------
    # Fallback: profile links anywhere
    # -----------------------
    if not authors:
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]

            if "/profile/" in href:
                name = a_tag.get_text(strip=True)

                if name:
                    full_link = href if href.startswith("http") else "https://dl.acm.org" + href

                    if full_link not in seen:
                        seen.add(full_link)
                        authors.append({
                            "name": name,
                            "author_link": full_link
                        })

    return authors

       



def main():
    seen_authors = set()
    rows = []

    
    files = [
        f for f in os.listdir(HTML_FOLDER)
        if f.endswith(".html")
    ]

    # Preserve download order
    files.sort(key=lambda x: os.path.getctime(os.path.join(HTML_FOLDER, x)))

    print(f"Processing {len(files)} files...\n")

    for filename in files:
        file_path = os.path.join(HTML_FOLDER, filename)

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, "html.parser")

        authors = extract_authors(soup)

        if not authors:
            print(f"No authors found in {filename}")
            continue

        for author in authors:
            # Use best unique identifier
            author_id = author["author_link"] or author["name"].lower()

            if author_id not in seen_authors:
                seen_authors.add(author_id)

                rows.append([
                    author["name"],
                    author["author_link"],
                    filename
                ])

    
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["author_name", "author_link", "source_file"])
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} unique authors to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()