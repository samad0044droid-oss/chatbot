"""Website crawler + chunker + theme-agnostic product/plugin counter."""

import re
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ClientChatbotCrawler/1.0)"}

PRODUCT_URL_PATTERNS = [
    re.compile(r"/product/[^/]+/?$"),
    re.compile(r"/products/[^/]+/?$"),
]

CATEGORY_URL_PATTERN = re.compile(r"/product-category/([^/]+)/?")

RESULT_COUNT_PATTERNS = [
    re.compile(r"of\s+([\d,]+)\s+results?", re.IGNORECASE),
    re.compile(r"Showing all\s+([\d,]+)\s+results?", re.IGNORECASE),
    re.compile(r"([\d,]+)\s+results?\s+found", re.IGNORECASE),
]


def extract_result_count(soup):
    text = soup.get_text(separator=" ")
    for pattern in RESULT_COUNT_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def is_same_domain(base_netloc, url):
    return urlparse(url).netloc in ("", base_netloc)


def clean_text(soup):
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def is_product_url(path):
    return any(p.search(path) for p in PRODUCT_URL_PATTERNS)


def detect_theme_color(soup):
    meta = soup.find("meta", attrs={"name": "theme-color"})
    if meta and meta.get("content"):
        return meta["content"].strip()

    for style_tag in soup.find_all("style"):
        text = style_tag.string or ""
        match = re.search(
            r"--(?:e-global-color-primary|primary-color|theme-color)\s*:\s*(#[0-9a-fA-F]{3,6})",
            text,
        )
        if match:
            return match.group(1)

    return "#2563eb"


def crawl_website(start_url, max_pages=30):
    base_netloc = urlparse(start_url).netloc
    visited = set()
    queue = deque([start_url])
    pages = []
    product_links_by_page = {}
    category_result_counts = {}
    theme_color = None

    while queue and len(visited) < max_pages:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=8)
            resp.raise_for_status()
        except Exception:
            continue

        if "text/html" not in resp.headers.get("Content-Type", ""):
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        if theme_color is None:
            theme_color = detect_theme_color(soup)

        cat_match = CATEGORY_URL_PATTERN.search(urlparse(url).path)
        if cat_match:
            true_count = extract_result_count(soup)
            if true_count is not None:
                slug = cat_match.group(1)
                category_result_counts[slug] = max(
                    true_count, category_result_counts.get(slug, 0)
                )

        page_product_urls = set()
        for link in soup.find_all("a", href=True):
            next_url = urljoin(url, link["href"]).split("#")[0]
            if not is_same_domain(base_netloc, next_url):
                continue
            path = urlparse(next_url).path
            if is_product_url(path):
                page_product_urls.add(next_url)
            if next_url not in visited:
                queue.append(next_url)

        if page_product_urls:
            product_links_by_page[url] = page_product_urls

        text = clean_text(soup)
        if text:
            pages.append((url, text))

    return pages, product_links_by_page, category_result_counts, (theme_color or "#2563eb")


def build_count_chunks(product_links_by_page, category_result_counts):
    chunks = []

    all_product_urls = set()
    category_urls = {}

    for page_url, product_urls in product_links_by_page.items():
        all_product_urls.update(product_urls)

        cat_match = CATEGORY_URL_PATTERN.search(urlparse(page_url).path)
        if cat_match:
            slug = cat_match.group(1)
            category_urls.setdefault(slug, set()).update(product_urls)

    if all_product_urls:
        sample = sorted(all_product_urls)[:15]
        sample_names = [urlparse(u).path.rstrip("/").split("/")[-1].replace("-", " ") for u in sample]
        chunks.append({
            "url": "site-wide",
            "text": (
                f"[GINTI INFO — poori website]: Crawl ke dauran kam se kam "
                f"{len(all_product_urls)} unique products/plugins/items "
                f"discover hue (yeh minimum hai, asal ginti categories ke "
                f"totals jama karne se milegi). Kuch namoone: "
                + "; ".join(sample_names)
            ),
            "is_count": True,
        })

    all_slugs = set(category_urls.keys()) | set(category_result_counts.keys())
    for slug in all_slugs:
        readable = slug.replace("-", " ")
        true_count = category_result_counts.get(slug)
        crawled_count = len(category_urls.get(slug, []))
        final_count = true_count if true_count is not None else crawled_count
        chunks.append({
            "url": f"category:{slug}",
            "text": (
                f"[GINTI INFO — category '{readable}']: Is category mein "
                f"total {final_count} products/items hain (website ke "
                f"apne result-count se confirm kiya gaya)."
            ),
            "is_count": True,
        })

    return chunks


def chunk_pages(pages, chunk_size=400):
    chunks = []
    for url, text in pages:
        words = text.split()
        for i in range(0, len(words), chunk_size):
            piece = " ".join(words[i:i + chunk_size])
            if piece.strip():
                chunks.append({"url": url, "text": piece, "is_count": False})
    return chunks