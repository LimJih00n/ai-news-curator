#!/usr/bin/env python3
"""
Notion과 Telegram 출력 테스트
"""

import os
from dotenv import load_dotenv
from datetime import datetime
from src.models import ContentItem, ArxivItem
from src.sinks.notion_sink import NotionSink
from src.sinks.telegram_sink import TelegramSink

def test_outputs():
    load_dotenv()

    print("="*60)
    print("[TEST] Notion & Telegram 출력 테스트")
    print("="*60)

    # 테스트용 샘플 데이터 생성
    test_items = [
        ContentItem(
            source="OpenAI Blog",
            title="GPT-4o mini performance improvements announced",
            link="https://openai.com/blog/gpt-4o-mini",
            published_at=datetime.now(),
            raw_content="New improvements in reasoning and coding capabilities",
            summary="GPT-4o mini가 추론과 코딩 능력에서 크게 개선되었다. 특히 함수 호출과 구조화된 출력에서 성능이 향상되었다."
        ),
        ContentItem(
            source="Anthropic Blog",
            title="Claude 3.5 Sonnet now supports 200k context window",
            link="https://anthropic.com/claude",
            published_at=datetime.now(),
            raw_content="Major update enables processing entire codebases at once",
            summary="Claude 3.5 Sonnet이 200k 토큰 컨텍스트를 지원한다. 전체 코드베이스를 한 번에 처리할 수 있게 되었다."
        ),
        ContentItem(
            source="LangChain Blog",
            title="New RAG optimization features for better retrieval",
            link="https://langchain.com/blog/rag",
            published_at=datetime.now(),
            raw_content="10x faster vector search with new indexing algorithm",
            summary="LangChain이 새로운 RAG 최적화 기능을 출시했다. 벡터 검색이 10배 빨라졌다."
        )
    ]

    # 논문 샘플 추가
    test_papers = [
        ArxivItem(
            source="arXiv",
            title="Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
            link="https://arxiv.org/abs/2201.11903",
            published_at=datetime.now(),
            abstract="We explore how generating a chain of thought improves performance",
            authors=["Jason Wei", "Xuezhi Wang", "Dale Schuurmans"],
            summary="Chain-of-Thought 프롬프팅이 LLM의 추론 능력을 크게 향상시킨다는 연구. 수학과 상식 추론에서 획기적인 성능 개선을 보였다.",
            categories=["cs.CL", "cs.AI"]
        )
    ]

    # 중요도 점수 추가
    for i, item in enumerate(test_items):
        item.importance_score = 4.5 - (i * 0.5)  # 4.5, 4.0, 3.5

    for paper in test_papers:
        paper.importance_score = 4.8

    # 오늘 날짜로 제목 생성
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"[TEST] AI-IT-Digest - {today}"

    # 1. Notion 테스트
    print("\n[1] Notion 테스트")
    print("-"*40)

    notion_secret = os.getenv("NOTION_INTEGRATION_SECRET")
    notion_db_id = os.getenv("NOTION_DATABASE_ID")

    if notion_secret and notion_db_id:
        print(f"Notion 설정 확인:")
        print(f"  - Integration Secret: {notion_secret[:10]}...")
        print(f"  - Database ID: {notion_db_id}")

        try:
            notion_sink = NotionSink(notion_secret, notion_db_id)

            # 섹션별로 구분해서 저장
            notion_sink.create_page_with_sections(
                title=title,
                news_items=test_items,
                paper_items=test_papers
            )

            print("[OK] Notion 페이지 생성 성공!")
            print(f"  제목: {title}")
            print(f"  뉴스: {len(test_items)}개")
            print(f"  논문: {len(test_papers)}개")

        except Exception as e:
            print(f"[ERROR] Notion 실패: {e}")

    else:
        print("[SKIP] Notion 설정 없음")
        if not notion_secret:
            print("  - NOTION_INTEGRATION_SECRET 없음")
        if not notion_db_id:
            print("  - NOTION_DATABASE_ID 없음")

    # 2. Telegram 테스트
    print("\n[2] Telegram 테스트")
    print("-"*40)

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if telegram_token and telegram_chat_id:
        print(f"Telegram 설정 확인:")
        print(f"  - Bot Token: {telegram_token[:10]}...")
        print(f"  - Chat ID: {telegram_chat_id}")

        try:
            telegram_sink = TelegramSink(telegram_token, telegram_chat_id)

            # Notion URL 생성 (있는 경우)
            notion_url = None
            if notion_db_id:
                notion_url = f"https://www.notion.so/{notion_db_id.replace('-', '')}"

            # 섹션별로 구분해서 전송
            telegram_sink.send_digest_separated(
                title=title,
                news_items=test_items[:2],  # 텔레그램은 상위 2개만
                paper_items=test_papers[:1],  # 논문 1개
                notion_url=notion_url
            )

            print("[OK] Telegram 메시지 전송 성공!")
            print(f"  제목: {title}")
            print(f"  뉴스: {len(test_items[:2])}개")
            print(f"  논문: {len(test_papers[:1])}개")

        except Exception as e:
            print(f"[ERROR] Telegram 실패: {e}")

    else:
        print("[SKIP] Telegram 설정 없음")
        if not telegram_token:
            print("  - TELEGRAM_BOT_TOKEN 없음")
        if not telegram_chat_id:
            print("  - TELEGRAM_CHAT_ID 없음")

    # 3. 요약
    print("\n" + "="*60)
    print("[SUMMARY] 테스트 결과")
    print("="*60)

    results = {
        "Notion": "성공" if notion_secret and notion_db_id else "스킵",
        "Telegram": "성공" if telegram_token and telegram_chat_id else "스킵",
        "테스트 데이터": f"뉴스 {len(test_items)}개, 논문 {len(test_papers)}개"
    }

    for key, value in results.items():
        print(f"  {key}: {value}")

    print("\n[DONE] 테스트 완료!")

    return results

if __name__ == "__main__":
    test_outputs()