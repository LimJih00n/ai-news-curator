#!/usr/bin/env python3
"""Notion API 연결 테스트 스크립트"""

import os
from dotenv import load_dotenv
from notion_client import Client
from datetime import datetime

def test_notion_connection():
    load_dotenv()

    # 환경 변수 확인
    secret = os.getenv("NOTION_INTEGRATION_SECRET")
    db_id = os.getenv("NOTION_DATABASE_ID")

    print(f"[환경 변수 확인]")
    print(f"- NOTION_INTEGRATION_SECRET: {'OK' if secret else 'MISSING'} ({secret[:10]}...)" if secret else "MISSING")
    print(f"- NOTION_DATABASE_ID: {'OK' if db_id else 'MISSING'} ({db_id})" if db_id else "MISSING")

    if not secret or not db_id:
        print("\n[ERROR] 환경 변수가 설정되지 않았습니다!")
        return

    # Notion 클라이언트 생성
    client = Client(auth=secret)

    # 데이터베이스 ID 포맷팅
    def format_database_id(database_id: str) -> str:
        clean_id = database_id.replace("-", "")
        if len(clean_id) == 32:
            return f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
        return database_id

    formatted_db_id = format_database_id(db_id)
    print(f"\n[데이터베이스 ID 포맷팅]")
    print(f"- 원본: {db_id}")
    print(f"- 포맷: {formatted_db_id}")

    # 1. 데이터베이스 정보 가져오기
    try:
        print(f"\n[1. 데이터베이스 정보 조회]")
        db_info = client.databases.retrieve(database_id=formatted_db_id)

        properties = db_info.get("properties", {})
        print(f"- 속성 개수: {len(properties)}")
        print(f"- 속성 목록:")

        title_property = None
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get("type")
            print(f"  * {prop_name}: {prop_type}")
            if prop_type == "title":
                title_property = prop_name

        print(f"- Title 속성: {title_property}")

    except Exception as e:
        print(f"[ERROR] 데이터베이스 정보 조회 실패:")
        print(f"  에러: {e}")
        print(f"  타입: {type(e).__name__}")
        return

    # 2. 기존 페이지 목록 조회
    try:
        print(f"\n[2. 기존 페이지 조회]")
        existing_pages = client.databases.query(
            database_id=formatted_db_id,
            page_size=5
        )

        page_count = len(existing_pages.get('results', []))
        print(f"- 페이지 수: {page_count}")

        if page_count > 0:
            for i, page in enumerate(existing_pages['results'][:3], 1):
                title_prop = page['properties'].get(title_property, {})
                if title_prop and title_prop.get('title'):
                    title_text = title_prop['title'][0].get('text', {}).get('content', 'No title')
                    print(f"  {i}. {title_text}")

    except Exception as e:
        print(f"[ERROR] 페이지 조회 실패: {e}")

    # 3. 테스트 페이지 생성
    try:
        print(f"\n[3. 테스트 페이지 생성]")

        test_title = f"[테스트] AI News Curator - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # 간단한 콘텐츠 생성
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "테스트 페이지입니다."}}
                    ]
                }
            },
            {
                "object": "block",
                "type": "divider",
                "divider": {}
            },
            {
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": "토글 테스트"}}],
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": "토글 내부 콘텐츠"}}
                                ]
                            }
                        }
                    ]
                }
            }
        ]

        # 페이지 생성
        page_properties = {
            title_property: {"title": [{"text": {"content": test_title}}]}
        }

        response = client.pages.create(
            parent={"database_id": formatted_db_id},
            properties=page_properties,
            children=children
        )

        print(f"- 페이지 생성 성공!")
        print(f"- 제목: {test_title}")
        print(f"- URL: {response.get('url', 'No URL')}")

    except Exception as e:
        print(f"[ERROR] 페이지 생성 실패:")
        print(f"  에러: {e}")
        print(f"  타입: {type(e).__name__}")

        # 상세 에러 정보
        if hasattr(e, 'response'):
            print(f"  응답: {e.response}")
        if hasattr(e, 'code'):
            print(f"  코드: {e.code}")
        if hasattr(e, 'body'):
            print(f"  본문: {e.body}")

if __name__ == "__main__":
    test_notion_connection()