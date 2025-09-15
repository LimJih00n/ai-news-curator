#!/usr/bin/env python3
"""
향상된 파이프라인 테스트
- 기존 뉴스 + 무료 인사이트 + 연결 엔진
"""

import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# 기존 모듈
from src.collectors.rss_collector import fetch_many
from src.collectors.content_filter import get_filtered_items
from src.models import ContentItem

# 새 모듈
from src.collectors.free_insight_collector import FreeInsightCollector
from src.collectors.podcast_collector import PodcastCollector
from src.insights.connection_engine import InsightConnectionEngine

def test_enhanced_pipeline():
    load_dotenv()

    print("="*60)
    print("[TEST] AI News Curator - Enhanced Pipeline Test")
    print("="*60)

    # 1. 기존 RSS 뉴스 수집
    print("\n[1] RSS 뉴스 수집...")
    rss_feeds = [
        'https://news.ycombinator.com/rss',
        'https://ai.googleblog.com/atom.xml',
        'https://openai.com/blog/rss.xml'
    ]

    rss_items = []
    for feed in rss_feeds:
        try:
            items = fetch_many([feed])
            rss_items.extend(items[:3])  # 각 피드당 3개씩만
        except:
            pass

    print(f"   [OK] RSS 뉴스: {len(rss_items)}개 수집")

    # 2. 무료 인사이트 수집
    print("\n[2] 무료 인사이트 수집...")
    free_collector = FreeInsightCollector()
    free_insights = free_collector.get_top_insights(min_quality=7.0)

    # FreeInsight를 ContentItem으로 변환
    insight_items = []
    for insight in free_insights[:5]:  # 상위 5개만
        item = ContentItem(
            source=insight.source,
            title=insight.title,
            link=insight.url,
            published_at=insight.published_at,
            raw_content=insight.content
        )
        # 품질 점수 추가
        item.importance_score = insight.quality_score
        item.topics = insight.topics
        insight_items.append(item)

    print(f"   [OK] 고품질 인사이트: {len(insight_items)}개 수집")

    # 인사이트 소스 출력
    sources = list(set([i.source for i in insight_items]))
    print(f"   소스: {', '.join(sources[:3])}")

    # 3. 팟캐스트 수집 (선택)
    print("\n[3] 팟캐스트 수집...")
    podcast_items = []
    try:
        podcast_collector = PodcastCollector()
        podcasts = podcast_collector.collect_recent_episodes(days_back=7)

        for podcast in podcasts[:2]:  # 상위 2개만
            item = ContentItem(
                source=f"Podcast: {podcast.podcast_name}",
                title=podcast.episode_title,
                link=podcast.url,
                published_at=podcast.published_at,
                raw_content=' '.join(podcast.key_insights) if podcast.key_insights else podcast.summary
            )
            item.importance_score = 7.0  # 팟캐스트는 기본 7점
            podcast_items.append(item)

        print(f"   [OK] 팟캐스트: {len(podcast_items)}개 수집")
    except Exception as e:
        print(f"   [WARN] 팟캐스트 수집 실패: {e}")

    # 4. 모든 아이템 통합
    all_items = rss_items + insight_items + podcast_items
    print(f"\n[4] 전체 통합: {len(all_items)}개 아이템")

    # 5. 날짜 필터링 (30일 이내만)
    cutoff_date = datetime.now() - timedelta(days=30)
    filtered_by_date = []

    for item in all_items:
        if hasattr(item, 'published_at') and item.published_at:
            if item.published_at > cutoff_date:
                filtered_by_date.append(item)
        else:
            filtered_by_date.append(item)  # 날짜 없으면 포함

    print(f"   [OK] 날짜 필터링 후: {len(filtered_by_date)}개")

    # 6. AI 필터링 (OpenAI API 필요)
    if os.getenv('OPENAI_API_KEY'):
        print("\n[5] AI 필터링...")
        try:
            top_items = get_filtered_items(
                os.getenv('OPENAI_API_KEY'),
                filtered_by_date,
                max_items=10
            )
            print(f"   [OK] AI 선별: {len(top_items)}개")
        except Exception as e:
            print(f"   [WARN] AI 필터링 실패: {e}")
            top_items = filtered_by_date[:10]
    else:
        print("\n[5] AI 필터링 스킵 (API 키 없음)")
        top_items = filtered_by_date[:10]

    # 7. 인사이트 연결 엔진
    print("\n[6] 인사이트 연결 분석...")
    try:
        engine = InsightConnectionEngine()

        # Dict로 변환 (engine이 요구하는 형식)
        item_dicts = []
        for item in top_items:
            item_dict = {
                'title': item.title,
                'content': item.raw_content or item.title,
                'source': item.source,
                'published_at': item.published_at if hasattr(item, 'published_at') else datetime.now(),
                'link': item.link
            }
            if hasattr(item, 'topics'):
                item_dict['topics'] = item.topics
            item_dicts.append(item_dict)

        connected_insights = engine.find_connections(item_dicts)

        print(f"   [OK] 연결된 인사이트: {len(connected_insights)}개 발견")

        # 연결 인사이트 출력
        for insight in connected_insights[:3]:
            print(f"\n   [{insight.insight_type.upper()}] {insight.title}")
            print(f"   연결 이유: {insight.connection_reason}")
            print(f"   신뢰도: {insight.confidence:.1%}")
    except Exception as e:
        print(f"   [WARN] 연결 분석 실패: {e}")

    # 8. 최종 결과 요약
    print("\n" + "="*60)
    print("[SUMMARY] 테스트 결과 요약")
    print("="*60)

    print(f"\n최종 선별된 TOP 5 아이템:\n")
    for i, item in enumerate(top_items[:5], 1):
        score = getattr(item, 'importance_score', 0)
        print(f"{i}. [{score:.1f}] {item.title[:60]}...")
        print(f"   출처: {item.source}")
        if hasattr(item, 'topics') and item.topics:
            print(f"   주제: {', '.join(item.topics)}")

    print("\n[DONE] 테스트 완료!")

    return {
        'rss_count': len(rss_items),
        'insight_count': len(insight_items),
        'podcast_count': len(podcast_items),
        'total_count': len(all_items),
        'filtered_count': len(top_items),
        'connected_insights': len(connected_insights) if 'connected_insights' in locals() else 0
    }

if __name__ == "__main__":
    results = test_enhanced_pipeline()

    print("\n[STATS] 통계:")
    for key, value in results.items():
        print(f"   {key}: {value}")