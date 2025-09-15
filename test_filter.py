#!/usr/bin/env python3
"""뉴스 필터링 테스트"""

import os
from dotenv import load_dotenv
from src.collectors.content_filter import get_filtered_items
from src.models import ContentItem
from datetime import datetime

# 테스트용 샘플 뉴스
test_items = [
    ContentItem(
        title="OpenAI releases GPT-4o mini with improved reasoning",
        raw_content="New model shows significant improvements in coding tasks",
        link="https://example.com/1",
        source="OpenAI Blog",
        published_at=datetime(2025, 9, 15)
    ),
    ContentItem(
        title="Korean government announces new AI policy",
        raw_content="Government plans to invest in AI startups",
        link="https://example.com/2",
        source="Local News",
        published_at=datetime(2025, 9, 14)
    ),
    ContentItem(
        title="Cursor IDE adds new AI pair programming features",
        raw_content="Revolutionary code completion with context awareness",
        link="https://example.com/3",
        source="Tech Blog",
        published_at=datetime(2025, 9, 15)
    ),
    ContentItem(
        title="Samsung invests $10B in semiconductor factory",
        raw_content="New factory will produce chips for smartphones",
        link="https://example.com/4",
        source="Business News",
        published_at=datetime(2025, 9, 13)
    ),
    ContentItem(
        title="Tutorial: How to use ChatGPT for writing emails",
        raw_content="Simple guide for beginners",
        link="https://example.com/5",
        source="Tutorial Site",
        published_at=datetime(2025, 9, 10)
    ),
    ContentItem(
        title="LangChain releases new RAG optimization features",
        raw_content="10x faster vector search with new indexing algorithm",
        link="https://example.com/6",
        source="LangChain Blog",
        published_at=datetime(2025, 9, 15)
    ),
    ContentItem(
        title="Apple announces layoffs in hardware division",
        raw_content="Company restructuring affects 500 employees",
        link="https://example.com/7",
        source="Business News",
        published_at=datetime(2025, 9, 12)
    ),
    ContentItem(
        title="New paper: Chain-of-Thought improves LLM accuracy by 40%",
        raw_content="Research from Stanford shows breakthrough in reasoning",
        link="https://example.com/8",
        source="arXiv",
        published_at=datetime(2025, 9, 14)
    ),
    ContentItem(
        title="How I built a todo app with React",
        raw_content="Step by step tutorial for beginners",
        link="https://example.com/9",
        source="Dev.to",
        published_at=datetime(2025, 9, 8)
    ),
    ContentItem(
        title="Anthropic's Claude 3.5 Sonnet now supports 200k context window",
        raw_content="Major update enables processing entire codebases",
        link="https://example.com/10",
        source="Anthropic Blog",
        published_at=datetime(2025, 9, 15)
    )
]

def test_filtering():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("[ERROR] OPENAI_API_KEY not found")
        return

    print(f"[테스트] {len(test_items)}개 샘플 뉴스로 필터링 테스트")
    print("="*60)

    # 원본 아이템 출력
    print("\n[원본 뉴스]")
    for i, item in enumerate(test_items, 1):
        print(f"{i}. {item.title[:60]}...")

    print("\n" + "="*60)
    print("[필터링 시작]")

    # 필터링 실행
    filtered = get_filtered_items(api_key, test_items, max_items=5)

    print("\n" + "="*60)
    print(f"\n[필터링 결과] {len(filtered)}개 선별")

    for i, item in enumerate(filtered, 1):
        score = getattr(item, 'importance_score', 0)
        print(f"\n{i}. [점수: {score:.1f}] {item.title}")
        print(f"   출처: {item.source}")
        if hasattr(item, 'score_reason'):
            print(f"   이유: {item.score_reason}")

if __name__ == "__main__":
    test_filtering()