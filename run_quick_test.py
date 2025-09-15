#!/usr/bin/env python3
"""
빠른 실행을 위한 테스트 스크립트
최소한의 뉴스만 수집하여 테스트
"""

import os
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.collectors.rss_collector import fetch_many
from src.collectors.hackernews_collector import HackerNewsCollector
# from src.collectors.arxiv_collector import ArxivCollector
from src.collectors.content_filter import get_filtered_items
from src.sinks.notion_sink import NotionSink
from src.sinks.telegram_sink import TelegramSink
from src.models import ContentItem

def quick_test():
    load_dotenv()

    print("="*60)
    print("[QUICK TEST] AI News Curator - 빠른 테스트")
    print("="*60)

    # 1. HackerNews만 수집 (빠름)
    print("\n[1] HackerNews 수집...")
    hn_collector = HackerNewsCollector()
    hn_items = hn_collector.fetch_top_stories(limit=5, min_score=100)
    print(f"   수집: {len(hn_items)}개")

    # ContentItem으로 변환
    items = []
    for hn in hn_items:
        item = ContentItem(
            source="Hacker News",
            title=hn.title,
            link=hn.url,
            published_at=hn.created_at,
            raw_content=hn.title
        )
        item.importance_score = min(hn.score / 50, 5.0)
        items.append(item)

    # 2. 날짜 필터링 (30일 이내)
    cutoff = datetime.now() - timedelta(days=30)
    items = [i for i in items if i.published_at > cutoff]
    print(f"   날짜 필터: {len(items)}개")

    # 3. AI 필터링 (선택)
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key and len(items) > 0:
        print("\n[2] AI 필터링...")
        try:
            filtered = get_filtered_items(api_key, items, max_items=3)
            if filtered:
                items = filtered
                print(f"   AI 선별: {len(items)}개")
        except Exception as e:
            print(f"   AI 필터링 스킵: {e}")

    # 4. Notion 저장
    print("\n[3] Notion 저장...")
    notion_secret = os.getenv("NOTION_INTEGRATION_SECRET")
    notion_db_id = os.getenv("NOTION_DATABASE_ID")

    if notion_secret and notion_db_id:
        try:
            notion_sink = NotionSink(notion_secret, notion_db_id)
            title = f"[Quick Test] AI Digest - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            notion_sink.create_page_with_sections(
                title=title,
                news_items=items,
                paper_items=[]
            )
            print(f"   [OK] Notion 페이지 생성: {title}")
        except Exception as e:
            print(f"   [ERROR] Notion 실패: {e}")
    else:
        print("   [SKIP] Notion 설정 없음")

    # 5. Telegram 전송
    print("\n[4] Telegram 전송...")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if telegram_token and telegram_chat_id:
        try:
            telegram_sink = TelegramSink(telegram_token, telegram_chat_id)
            title = f"Quick Test - {datetime.now().strftime('%H:%M')}"

            telegram_sink.send_digest_separated(
                title=title,
                news_items=items[:2],
                paper_items=[],
                notion_url=None
            )
            print(f"   [OK] Telegram 메시지 전송")
        except Exception as e:
            print(f"   [ERROR] Telegram 실패: {e}")
    else:
        print("   [SKIP] Telegram 설정 없음")

    print("\n" + "="*60)
    print("[DONE] 빠른 테스트 완료!")
    print("="*60)

    # 결과 요약
    print(f"\n최종 결과:")
    for i, item in enumerate(items[:3], 1):
        safe_title = item.title[:50].encode('cp949', 'ignore').decode('cp949')
        print(f"{i}. {safe_title}...")

if __name__ == "__main__":
    quick_test()