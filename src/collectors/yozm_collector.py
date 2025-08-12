from __future__ import annotations

from typing import List
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.collectors.rss_collector import RawItem


def _extract_article_links_from_magazine(list_url: str, html: str, max_links: int = 10) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    links: List[str] = []

    # Heuristic 1: any <a href="/magazine/..."> on the listing page
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if re.match(r"^/magazine/[^/#?]+/?$", href):
            abs_url = urljoin(list_url, href)
            links.append(abs_url)
        if len(links) >= max_links:
            break

    # de-dup while preserving order
    seen = set()
    deduped: List[str] = []
    for u in links:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped[:max_links]


def _extract_main_text(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")

    # Prefer article tag
    article = soup.find("article")
    if article:
        text = article.get_text(separator="\n", strip=True)
        if text:
            return text

    # Fallback: common content containers
    for selector in [
        "div.article-body",
        "div.content",
        "section.article",
        "div#content",
    ]:
        node = soup.select_one(selector)
        if node:
            text = node.get_text(separator="\n", strip=True)
            if text:
                return text

    # Fallback: meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return str(meta["content"]).strip()
    return None


def collect_latest_from_magazine(list_url: str, max_items: int = 10, timeout: int = 20) -> List[RawItem]:
    try:
        resp = requests.get(list_url, timeout=timeout)
        resp.raise_for_status()
    except Exception:
        return []

    article_links = _extract_article_links_from_magazine(list_url, resp.text, max_links=max_items)
    results: List[RawItem] = []
    for link in article_links:
        try:
            r = requests.get(link, timeout=timeout)
            r.raise_for_status()
        except Exception:
            continue

        title_match = re.search(r"<title>(.*?)</title>", r.text, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else link
        content = _extract_main_text(r.text)
        results.append(
            RawItem(
                source=list_url,
                title=title,
                link=link,
                published=None,
                content=content,
            )
        )

    return results


