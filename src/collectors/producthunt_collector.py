from __future__ import annotations

import requests
from typing import List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

@dataclass
class ProductHuntItem:
    """Product Hunt 아이템 데이터 클래스"""
    id: str
    title: str
    tagline: str
    url: str
    votes: int
    comments: int
    featured: bool
    created_at: datetime
    source: str = "Product Hunt"
    
    @property
    def link(self):
        """ContentItem과 호환성을 위한 property"""
        return self.url
    
    @property
    def published_at(self):
        """ContentItem과 호환성을 위한 property"""
        return self.created_at
    
    @property
    def content(self):
        """ContentItem과 호환성을 위한 property"""
        return f"{self.tagline} | Votes: {self.votes} | Comments: {self.comments}"


class ProductHuntCollector:
    """Product Hunt RSS를 통한 최신 제품 수집"""
    
    def __init__(self):
        self.rss_url = "https://www.producthunt.com/feed"
        self.session = requests.Session()
    
    def fetch_latest_products(self, limit: int = 10) -> List[ProductHuntItem]:
        """
        Product Hunt RSS에서 최신 제품 수집
        
        Args:
            limit: 가져올 최대 제품 수
        """
        try:
            import feedparser
            
            print("[PH] Product Hunt 최신 제품 수집 중...")
            feed = feedparser.parse(self.rss_url)
            
            products = []
            for entry in feed.entries[:limit]:
                # RSS 엔트리에서 정보 추출
                product = self._parse_rss_entry(entry)
                if product:
                    products.append(product)
                    print(f"  PH: {product.title} - {product.tagline[:50]}...")
            
            return products
            
        except Exception as e:
            print(f"Product Hunt 수집 실패: {e}")
            return []
    
    def _parse_rss_entry(self, entry) -> Optional[ProductHuntItem]:
        """RSS 엔트리를 ProductHuntItem으로 파싱"""
        try:
            # 기본 정보 추출
            title = getattr(entry, 'title', '')

            # 이모지와 특수문자 제거 (Windows cp949 호환성)
            title = self._clean_text_for_windows(title)

            # 제목에서 tagline 분리 (보통 "Product Name - Tagline" 형식)
            if ' - ' in title:
                product_name, tagline = title.split(' - ', 1)
            else:
                product_name = title
                tagline = getattr(entry, 'summary', '')[:100]
                tagline = self._clean_text_for_windows(tagline)
            
            # 날짜 파싱
            published = getattr(entry, 'published_parsed', None)
            if published:
                import time
                created_at = datetime.fromtimestamp(time.mktime(published))
            else:
                created_at = datetime.now()
            
            # Product Hunt URL
            url = getattr(entry, 'link', '')
            
            # RSS에서는 투표수와 댓글수를 직접 얻을 수 없으므로 기본값 사용
            # 실제 운영 시에는 PH API를 사용하거나 스크래핑으로 보완 가능
            
            return ProductHuntItem(
                id=getattr(entry, 'id', url),
                title=product_name.strip(),
                tagline=tagline.strip(),
                url=url,
                votes=0,  # RSS에서는 제공되지 않음
                comments=0,  # RSS에서는 제공되지 않음
                featured=True,  # RSS에 나오는 것은 featured로 간주
                created_at=created_at
            )
            
        except Exception as e:
            print(f"RSS 엔트리 파싱 실패: {e}")
            return None

    def _clean_text_for_windows(self, text: str) -> str:
        """Windows cp949 호환을 위해 텍스트 정리"""
        if not text:
            return ""

        import re

        # 이모지와 특수 유니코드 문자 제거
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )

        # 이모지 제거
        text = emoji_pattern.sub(' ', text)

        # cp949로 인코딩 가능한 문자만 유지
        try:
            text.encode('cp949')
        except UnicodeEncodeError:
            # 문제가 되는 문자들을 안전한 문자로 대체
            text = text.encode('cp949', errors='replace').decode('cp949')

        # 연속된 공백을 하나로 정리
        text = re.sub(r'\s+', ' ', text).strip()

        return text
    
    def fetch_trending_categories(self) -> List[str]:
        """트렌딩 카테고리 목록 (하드코딩된 주요 카테고리)"""
        return [
            "AI & Machine Learning",
            "Developer Tools", 
            "Productivity",
            "No-Code",
            "Design Tools",
            "APIs & Backend",
            "Chrome Extensions",
            "Open Source"
        ]