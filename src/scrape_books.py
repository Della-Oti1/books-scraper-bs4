import time, csv, re, os
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

BASE = "https://books.toscrape.com/"
CATALOG = "https://books.toscrape.com/catalogue/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LearningScraper/1.0)"}

def get_soup(url: str) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException:
        return None

def normalize_price(txt: str) -> float:
    return float(re.sub(r"[^\d.]", "", txt))

def scrape_page(url: str) -> List[Dict]:
    soup = get_soup(url)
    if not soup:
        return []
    items = []
    for article in soup.select("article.product_pod"):
        title = article.h3.a["title"].strip()
        rel = article.h3.a["href"].replace("../../../", "")
        product_url = CATALOG + rel
        price = article.select_one(".price_color").get_text(strip=True)
        stock = article.select_one(".availability").get_text(strip=True)

        detail = get_soup(product_url)
        rating = category = description = None
        if detail:
            r = detail.select_one(".product_main .star-rating")
            if r:
                stars = [c for c in r.get("class", []) if c != "star-rating"]
                rating = stars[0] if stars else None
            bc = detail.select("ul.breadcrumb li a")
            if len(bc) >= 3:
                category = bc[2].get_text(strip=True)
            d = detail.select_one("#product_description")
            if d:
                p = d.find_next_sibling("p")
                if p:
                    description = p.get_text(strip=True)

        items.append({
            "title": title,
            "price_gbp": normalize_price(price),
            "stock": stock,
            "rating": rating,
            "category": category,
            "description": description,
            "product_url": product_url
        })
        time.sleep(0.1)
    return items

def next_page_url(soup: BeautifulSoup, current_url: str):
    nxt = soup.select_one("li.next a")
    if not nxt:
        return None
    href = nxt["href"]
    base = current_url.rsplit("/", 1)[0] + "/" if "catalogue" in current_url else BASE
    return base + href

def main():
    os.makedirs("data", exist_ok=True)
    out_csv = "data/books.csv"
    url = BASE + "catalogue/page-1.html"
    rows: List[Dict] = []
    page = 1
    while url:
        soup = get_soup(url)
        if not soup:
            break
        rows.extend(scrape_page(url))
        url = next_page_url(soup, url)
        page += 1
        time.sleep(0.2)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "title","price_gbp","stock","rating","category","description","product_url"
        ])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out_csv} ({len(rows)} rows)")

if __name__ == "__main__":
    main()
