from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List
import datetime as dt
import feedparser
import requests


@dataclass
class RawItem:
    source: str
    title: str
    link: str
    published: str | None
    content: str | None


def fetch_feed(url: str, timeout: int = 20, max_age_days: int = 30) -> List[RawItem]:
    """RSS 피드를 가져와서 최신 항목만 필터링"""
    feed = feedparser.parse(url)
    items: List[RawItem] = []
    
    # 현재 시간
    from datetime import datetime, timedelta
    import time
    now = datetime.now()
    cutoff_date = now - timedelta(days=max_age_days)
    
    for e in feed.entries:
        # 날짜 확인
        published_parsed = getattr(e, "published_parsed", None)
        if published_parsed:
            try:
                # feedparser의 time_struct를 datetime으로 변환
                published_date = datetime.fromtimestamp(time.mktime(published_parsed))
                
                # 너무 오래된 항목은 건너뛰기
                if published_date < cutoff_date:
                    print(f"  Skipping old item from {url}: {e.title[:50]}... ({published_date.strftime('%Y-%m-%d')})")
                    continue
                    
                # 미래 날짜도 건너뛰기 (잘못된 데이터)
                if published_date > now + timedelta(days=1):
                    print(f"  Skipping future item from {url}: {e.title[:50]}... ({published_date.strftime('%Y-%m-%d')})")
                    continue
                    
            except Exception as date_error:
                # 날짜 파싱 실패시 그냥 포함 (최신일 가능성)
                pass
        
        content = None
        if hasattr(e, "content") and e.content:
            content = e.content[0].value
        elif hasattr(e, "summary"):
            content = e.summary
            
        items.append(
            RawItem(
                source=url,
                title=getattr(e, "title", ""),
                link=getattr(e, "link", ""),
                published=getattr(e, "published", None),
                content=content,
            )
        )
    return items


def fetch_many(urls: Iterable[str]) -> List[RawItem]:
    all_items: List[RawItem] = []
    for u in urls:
        try:
            all_items.extend(fetch_feed(u))
        except Exception:
            continue
    return all_items
