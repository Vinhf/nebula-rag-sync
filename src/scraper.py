import requests
import json
from pathlib import Path
import hashlib
from urllib.parse import urlparse, urljoin
from markdownify import markdownify as md
from datetime import datetime
import re
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://support.optisigns.com/hc/en-us"

ARTICLES_DIR = Path(__file__).parent.parent / "articles" 
ARTICLES_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "OptiBot-Scraper/1.0 (for take-home test; contact: thanhvinh1662003@gmail.com)"
}

import re
import unicodedata

def slugify(text: str, max_length: int = 100) -> str:
    """
    Tạo slug an toàn, hỗ trợ Unicode (tiếng Việt, Latin có dấu, v.v.).
    - Chuyển tất cả ký tự có dấu → không dấu (transliterate).
    - Lowercase, chỉ giữ a-z0-9 và dấu gạch ngang.
    - Thay nhiều khoảng trắng/dấu bằng 1 dấu gạch ngang.
    - Loại bỏ dấu gạch ngang ở đầu/cuối.
    - Tránh slug rỗng → fallback thành 'article'.
    """
    if not text or not text.strip():
        return "article"

    # Bước 1: Normalize Unicode → phân tách dấu (NFKD) và bỏ dấu (encode ascii ignore)
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')

    # Bước 2: Lowercase
    text = text.lower()

    # Bước 3: Thay mọi thứ không phải a-z0-9 hoặc space bằng dấu cách
    text = re.sub(r'[^a-z0-9\s-]', ' ', text)

    # Bước 4: Thay nhiều khoảng trắng + dấu gạch ngang liên tiếp → 1 dấu gạch ngang
    text = re.sub(r'[\s-]+', '-', text)

    # Bước 5: Loại bỏ dấu gạch ngang ở đầu và cuối
    text = text.strip('-')

    # Bước 6: Cắt độ dài nếu cần
    text = text[:max_length]

    # Bước 7: Nếu sau tất cả vẫn rỗng → fallback
    return text if text else "article"


def clean_html_for_markdown(html: str) -> str:
    """Tùy chọn: tiền xử lý HTML trước khi convert (nếu cần loại bỏ phần thừa)"""
    # Ví dụ: loại bỏ một số class Zendesk inject không cần
    html = re.sub(r'<div class="[^"]*article-body[^"]*">', '', html)
    html = re.sub(r'</div>\s*$', '', html, flags=re.MULTILINE)
    return html.strip()


def convert_to_markdown(html_content: str, article_url: str) -> str:
    """
    Convert HTML → Markdown, giữ heading, code block, link (relative nếu có thể)
    """
    # markdownify config
    markdown = md(
        html_content,
        heading_style="ATX",           # # Heading
        strip=["script", "style"],     # loại bỏ script/style
        autolink=True,
        bullets=["- ", "* ", "+ "],    # dùng dấu - cho list
    )

    # Giữ relative link nếu link nội bộ (tùy chọn nâng cao)
    # Ví dụ: thay https://support.optisigns.com/... bằng /hc/en-us/...
    # Nhưng ở đây ta giữ nguyên full URL cho an toàn

    return markdown.strip()


def save_article(article: dict):
    """Lưu 1 bài viết thành .md và .meta.json"""
    title = article.get("title", "Untitled")
    slug = slugify(title)
    if not slug:
        slug = f"article-{article['id']}"

    md_path = ARTICLES_DIR / f"{slug}.md"
    meta_path = ARTICLES_DIR / f"{slug}.meta.json"

    # Nội dung Markdown
    html_body = article.get("body") or article.get("html_body", "")
    if not html_body:
        logger.warning(f"Article {title} has no body, skipping content")
        content_md = ""
    else:
        cleaned_html = clean_html_for_markdown(html_body)
        content_md = convert_to_markdown(cleaned_html, article["html_url"])

    # Thêm header metadata vào file .md (dễ đọc và cite)
    front_matter = f"""---
title: {title}
article_id: {article['id']}
url: {article['html_url']}
updated_at: {article['updated_at']}
---

# {title}

**Article URL:** {article['html_url']}

{content_md}
"""

    # Lưu file Markdown
    md_path.write_text(front_matter, encoding="utf-8")
    logger.info(f"Saved Markdown: {md_path.name}")

    # Lưu metadata để detect thay đổi sau
    meta = {
        "id": article["id"],
        "title": title,
        "slug": slug,
        "html_url": article["html_url"],
        "api_url": article["url"],
        "updated_at": article["updated_at"],
        "content_hash": hashlib.sha256(front_matter.encode("utf-8")).hexdigest(),
        "last_scraped": datetime.utcnow().isoformat() + "Z",
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Saved meta: {meta_path.name}")

    return slug, meta


def scrape_all_articles(max_articles: int = 30, max_pages: int = 10):
    """Scrape chỉ tối đa max_articles bài viết"""
    page = 1
    added_count = 0

    while True:
        url = f"{BASE_URL}/articles.json?page={page}&per_page=100"
        logger.info(f"Fetching page {page}: {url}")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Error fetching page {page}: {e}")
            break

        articles = data.get("articles", [])
        if not articles:
            logger.info("No more articles.")
            break

        for article in articles:
            if added_count >= max_articles:
                logger.info(f"Đã đạt giới hạn {max_articles} bài. Dừng scrape.")
                return added_count

            if article.get("draft") or article.get("outdated"):
                logger.debug(f"Skipping draft/outdated: {article['title']}")
                continue

            save_article(article)
            added_count += 1

        # Pagination check
        next_page_url = data.get("next_page")
        if not next_page_url or page >= max_pages:
            logger.info(f"Reached end or max_pages. Total saved: {added_count}")
            break

        page += 1

    return added_count


if __name__ == "__main__":
    logger.info("Starting scraper...")
    total = scrape_all_articles(max_articles=30, max_pages=10)
    logger.info(f"Scraper finished. Total articles processed: {total}")