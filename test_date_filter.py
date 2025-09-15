#!/usr/bin/env python3
"""날짜 기반 필터링 테스트"""

import os
from dotenv import load_dotenv
from src.collectors.content_filter import simple_keyword_filter
from src.models import ContentItem
from datetime import datetime, timedelta

# 다양한 날짜의 테스트 뉴스
test_items = [
    ContentItem(
        source="OpenAI Blog",
        title="GPT-4o mini released today with better performance",
        link="https://example.com/1",
        published_at=datetime.now(),  # 오늘
        raw_content="Brand new model just released"
    ),
    ContentItem(
        source="Tech Blog",
        title="Cursor AI adds new features yesterday",
        link="https://example.com/2",
        published_at=datetime.now() - timedelta(days=1),  # 어제
        raw_content="New features added to Cursor"
    ),
    ContentItem(
        source="Old News",
        title="ChatGPT 3.5 was amazing when it launched",
        link="https://example.com/3",
        published_at=datetime.now() - timedelta(days=7),  # 1주일 전
        raw_content="Old news about ChatGPT"
    ),
    ContentItem(
        source="Very Old",
        title="jQuery 3.0 released with new features",
        link="https://example.com/4",
        published_at=datetime.now() - timedelta(days=60),  # 2달 전
        raw_content="Very old jQuery news"
    ),
    ContentItem(
        source="Ancient",
        title="Windows XP service pack 3 available",
        link="https://example.com/5",
        published_at=datetime.now() - timedelta(days=365),  # 1년 전
        raw_content="Ancient Windows XP news"
    ),
    ContentItem(
        source="Recent",
        title="Claude 3.5 Sonnet improvements announced",
        link="https://example.com/6",
        published_at=datetime.now() - timedelta(days=2),  # 2일 전
        raw_content="Recent Claude improvements"
    ),
    ContentItem(
        source="LangChain",
        title="LangChain releases new RAG features",
        link="https://example.com/7",
        published_at=datetime.now() - timedelta(hours=6),  # 6시간 전
        raw_content="Brand new RAG features"
    ),
    ContentItem(
        source="Medium Old",
        title="Stable Diffusion XL tutorial",
        link="https://example.com/8",
        published_at=datetime.now() - timedelta(days=30),  # 30일 전
        raw_content="Month old SD tutorial"
    ),
]

def test_date_filtering():
    print("[날짜 필터링 테스트]")
    print("="*60)

    # 원본 출력
    print("\n[원본 뉴스 - 날짜순]")
    for item in test_items:
        days_old = (datetime.now() - item.published_at).days
        if days_old == 0:
            age = "오늘"
        elif days_old == 1:
            age = "어제"
        elif days_old < 7:
            age = f"{days_old}일 전"
        elif days_old < 30:
            age = f"{days_old//7}주 전"
        elif days_old < 365:
            age = f"{days_old//30}달 전"
        else:
            age = f"{days_old//365}년 전"

        print(f"- [{age:8s}] {item.title[:50]}")

    print("\n" + "="*60)
    print("[키워드 필터링 적용 (날짜 가중치 포함)]")

    # 필터링 실행
    filtered = simple_keyword_filter(test_items, max_items=10)

    print(f"\n[필터링 결과] {len(filtered)}개 선별")
    for i, item in enumerate(filtered, 1):
        days_old = (datetime.now() - item.published_at).days
        if days_old == 0:
            age = "오늘"
        elif days_old == 1:
            age = "어제"
        elif days_old < 7:
            age = f"{days_old}일 전"
        elif days_old < 30:
            age = f"{days_old//7}주 전"
        elif days_old < 365:
            age = f"{days_old//30}달 전"
        else:
            age = f"{days_old//365}년 전"

        print(f"{i}. [{age:8s}] {item.title[:50]}")

if __name__ == "__main__":
    test_date_filtering()