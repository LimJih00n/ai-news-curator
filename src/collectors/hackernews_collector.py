from __future__ import annotations

import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
from dataclasses import dataclass

@dataclass
class HackerNewsItem:
    """Hacker News 아이템 데이터 클래스"""
    id: int
    title: str
    url: str
    score: int
    comments: int
    author: str
    created_at: datetime
    hn_url: str
    source: str = "Hacker News"
    
    @property
    def link(self):
        """ContentItem과 호환성을 위한 property"""
        return self.url or self.hn_url
    
    @property
    def published_at(self):
        """ContentItem과 호환성을 위한 property"""
        return self.created_at
    
    @property
    def content(self):
        """ContentItem과 호환성을 위한 property"""
        return f"Score: {self.score} | Comments: {self.comments} | By: {self.author}"


class HackerNewsCollector:
    """Hacker News API를 사용한 고품질 뉴스 수집"""
    
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self):
        self.session = requests.Session()
    
    def fetch_top_stories(self, limit: int = 30, min_score: int = 50) -> List[HackerNewsItem]:
        """
        HN Top Stories 수집 (점수와 댓글 수 기반 필터링)
        
        Args:
            limit: 가져올 최대 스토리 수
            min_score: 최소 점수 임계값
        """
        try:
            # Top stories ID 가져오기
            response = self.session.get(f"{self.BASE_URL}/topstories.json", timeout=10)
            story_ids = response.json()[:limit * 2]  # 필터링을 고려해 더 많이 가져옴
            
            stories = []
            for story_id in story_ids:
                if len(stories) >= limit:
                    break
                    
                story = self._fetch_story(story_id)
                if story and story.score >= min_score:
                    stories.append(story)
                    print(f"  HN: {story.title[:50]}... (Score: {story.score}, Comments: {story.comments})")
            
            # 점수순으로 정렬
            stories.sort(key=lambda x: x.score, reverse=True)
            return stories[:limit]
            
        except Exception as e:
            print(f"Hacker News 수집 실패: {e}")
            return []
    
    def fetch_best_stories(self, limit: int = 20) -> List[HackerNewsItem]:
        """
        HN Best Stories 수집 (높은 품질의 큐레이션된 콘텐츠)
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/beststories.json", timeout=10)
            story_ids = response.json()[:limit]
            
            stories = []
            for story_id in story_ids:
                story = self._fetch_story(story_id)
                if story:
                    stories.append(story)
            
            return stories
            
        except Exception as e:
            print(f"HN Best Stories 수집 실패: {e}")
            return []
    
    def fetch_show_hn(self, limit: int = 10) -> List[HackerNewsItem]:
        """
        Show HN 수집 (새로운 프로젝트와 런칭)
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/showstories.json", timeout=10)
            story_ids = response.json()[:limit]
            
            stories = []
            for story_id in story_ids:
                story = self._fetch_story(story_id)
                if story and "Show HN" in story.title:
                    stories.append(story)
            
            return stories
            
        except Exception as e:
            print(f"Show HN 수집 실패: {e}")
            return []
    
    def fetch_trending(self, hours: int = 6, min_velocity: float = 10.0) -> List[HackerNewsItem]:
        """
        트렌딩 스토리 수집 (시간당 점수 증가율 기반)
        
        Args:
            hours: 최근 N시간 이내 스토리
            min_velocity: 최소 시간당 점수 증가율
        """
        try:
            # New stories에서 최근 항목 가져오기
            response = self.session.get(f"{self.BASE_URL}/newstories.json", timeout=10)
            story_ids = response.json()[:100]
            
            trending = []
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            for story_id in story_ids:
                story = self._fetch_story(story_id)
                if not story:
                    continue
                
                # 시간당 점수 계산
                hours_old = (datetime.now() - story.created_at).total_seconds() / 3600
                if hours_old > 0 and hours_old <= hours:
                    velocity = story.score / hours_old
                    if velocity >= min_velocity:
                        trending.append(story)
                        print(f"  Trending: {story.title[:40]}... (Velocity: {velocity:.1f}/hr)")
            
            # Velocity 순으로 정렬
            trending.sort(key=lambda x: x.score / max(1, (datetime.now() - x.created_at).total_seconds() / 3600), reverse=True)
            return trending
            
        except Exception as e:
            print(f"Trending 수집 실패: {e}")
            return []
    
    def _fetch_story(self, story_id: int) -> Optional[HackerNewsItem]:
        """개별 스토리 정보 가져오기"""
        try:
            response = self.session.get(f"{self.BASE_URL}/item/{story_id}.json", timeout=5)
            data = response.json()
            
            if not data or data.get('type') != 'story':
                return None
            
            # 삭제되거나 dead 상태인 스토리 제외
            if data.get('deleted') or data.get('dead'):
                return None
            
            return HackerNewsItem(
                id=data['id'],
                title=data.get('title', ''),
                url=data.get('url', ''),
                score=data.get('score', 0),
                comments=data.get('descendants', 0),
                author=data.get('by', 'unknown'),
                created_at=datetime.fromtimestamp(data.get('time', 0)),
                hn_url=f"https://news.ycombinator.com/item?id={data['id']}"
            )
            
        except Exception as e:
            print(f"Story {story_id} 가져오기 실패: {e}")
            return None
    
    def fetch_hybrid(self, 
                    top_limit: int = 15,
                    best_limit: int = 5,
                    show_limit: int = 5,
                    trending_hours: int = 6) -> List[HackerNewsItem]:
        """
        하이브리드 수집: 다양한 소스에서 최적의 콘텐츠 조합
        """
        all_stories = []
        
        # 1. Top Stories (가장 중요)
        print("📊 Hacker News Top Stories 수집 중...")
        top_stories = self.fetch_top_stories(limit=top_limit, min_score=30)
        all_stories.extend(top_stories)
        
        # 2. Trending Stories (빠르게 상승 중인 스토리)
        print("🚀 Hacker News Trending Stories 수집 중...")
        trending = self.fetch_trending(hours=trending_hours, min_velocity=8.0)
        all_stories.extend(trending[:5])
        
        # 3. Show HN (새로운 프로젝트)
        print("🆕 Show HN 수집 중...")
        show_hn = self.fetch_show_hn(limit=show_limit)
        all_stories.extend(show_hn)
        
        # 4. Best Stories (큐레이션된 고품질)
        print("⭐ Hacker News Best Stories 수집 중...")
        best = self.fetch_best_stories(limit=best_limit)
        all_stories.extend(best)
        
        # 중복 제거 (ID 기반)
        seen_ids = set()
        unique_stories = []
        for story in all_stories:
            if story.id not in seen_ids:
                seen_ids.add(story.id)
                unique_stories.append(story)
        
        # 종합 점수로 정렬 (점수 + 댓글 + 최신성)
        def calculate_rank_score(story: HackerNewsItem) -> float:
            hours_old = (datetime.now() - story.created_at).total_seconds() / 3600
            time_penalty = max(1, hours_old / 24)  # 24시간이 지나면 패널티
            
            # 점수: 70%, 댓글: 20%, 시간: 10%
            rank_score = (story.score * 0.7 + story.comments * 0.2) / time_penalty
            return rank_score
        
        unique_stories.sort(key=calculate_rank_score, reverse=True)
        
        print(f"✅ Hacker News 수집 완료: {len(unique_stories)}개 고품질 스토리")
        return unique_stories