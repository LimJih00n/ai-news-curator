"""
데이터 소스 설정 로더
sources.yaml 파일에서 RSS 피드 정보를 읽어오는 모듈
"""

import yaml
import os
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class FeedSource:
    """RSS 피드 소스 정보"""
    name: str
    url: str
    items_per_fetch: int


@dataclass
class YouTubeChannel:
    """YouTube 채널 정보"""
    name: str
    url: str
    max_videos: int


@dataclass
class SourceConfig:
    """전체 소스 설정"""
    tech_news: List[FeedSource]
    ai_research: List[FeedSource]
    startup_innovation: List[FeedSource]
    academic_papers: List[FeedSource]
    youtube_channels: List[YouTubeChannel]
    google_news_queries: List[str]
    arxiv_query: str
    arxiv_max_results: int
    max_filtered_items: int


def load_sources_config(config_path: str = None) -> SourceConfig:
    """
    sources.yaml 파일에서 설정을 로드
    
    Args:
        config_path: 설정 파일 경로 (기본값: configs/sources.yaml)
    
    Returns:
        SourceConfig 객체
    """
    if config_path is None:
        # 기본 경로 설정
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "configs",
            "sources.yaml"
        )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # FeedSource 객체로 변환
    tech_news = [FeedSource(**item) for item in data.get('tech_news', [])]
    ai_research = [FeedSource(**item) for item in data.get('ai_research', [])]
    startup_innovation = [FeedSource(**item) for item in data.get('startup_innovation', [])]
    academic_papers = [FeedSource(**item) for item in data.get('academic_papers', [])]
    youtube_channels = [YouTubeChannel(**item) for item in data.get('youtube_channels', [])]
    
    return SourceConfig(
        tech_news=tech_news,
        ai_research=ai_research,
        startup_innovation=startup_innovation,
        academic_papers=academic_papers,
        youtube_channels=youtube_channels,
        google_news_queries=data.get('google_news_queries', []),
        arxiv_query=data.get('arxiv_query', ''),
        arxiv_max_results=data.get('arxiv_max_results', 10),
        max_filtered_items=data.get('max_filtered_items', 20)
    )


def get_all_feed_sources(config: SourceConfig) -> List[FeedSource]:
    """
    모든 피드 소스를 하나의 리스트로 반환
    
    Args:
        config: SourceConfig 객체
    
    Returns:
        모든 FeedSource 객체의 리스트
    """
    all_sources = []
    all_sources.extend(config.tech_news)
    all_sources.extend(config.ai_research)
    all_sources.extend(config.startup_innovation)
    all_sources.extend(config.academic_papers)
    return all_sources