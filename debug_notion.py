#!/usr/bin/env python3
"""
노션 연결 디버깅 스크립트
GitHub Actions 환경에서 실행하여 문제 진단
"""

import os
from dotenv import load_dotenv
from src.sinks.notion_sink import NotionSink

def debug_notion_connection():
    """노션 연결 상태 디버깅"""
    print("🔍 GitHub Actions 노션 연결 디버깅")
    print("=" * 50)
    
    # 환경변수 확인
    load_dotenv()  # 로컬 테스트용
    
    notion_secret = os.getenv('NOTION_INTEGRATION_SECRET')
    notion_db_id = os.getenv('NOTION_DATABASE_ID')
    
    print(f"1. 환경변수 확인:")
    print(f"   - NOTION_INTEGRATION_SECRET: {'✅' if notion_secret else '❌'}")
    if notion_secret:
        print(f"     길이: {len(notion_secret)} 글자")
        print(f"     시작: {notion_secret[:10]}...")
    
    print(f"   - NOTION_DATABASE_ID: {'✅' if notion_db_id else '❌'}")
    if notion_db_id:
        print(f"     값: {notion_db_id}")
    
    print()
    
    if not notion_secret or not notion_db_id:
        print("❌ 필수 환경변수가 누락되었습니다!")
        return False
    
    # 노션 연결 테스트
    print("2. Notion API 연결 테스트:")
    try:
        from notion_client import Client
        client = Client(auth=notion_secret)
        
        # 데이터베이스 접근 테스트
        print("   - Client 초기화: ✅")
        
        # 데이터베이스 ID 포맷팅
        clean_id = notion_db_id.replace("-", "")
        if len(clean_id) == 32:
            formatted_id = f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
        else:
            formatted_id = notion_db_id
        
        print(f"   - 포맷된 DB ID: {formatted_id}")
        
        # 데이터베이스 정보 조회
        db_info = client.databases.retrieve(database_id=formatted_id)
        print("   - 데이터베이스 조회: ✅")
        print(f"   - 데이터베이스 제목: {db_info.get('title', [{}])[0].get('plain_text', 'N/A')}")
        
        properties = db_info.get("properties", {})
        print(f"   - 속성 개수: {len(properties)}")
        print(f"   - 속성 목록: {list(properties.keys())}")
        
        # Title 속성 확인
        title_props = [name for name, info in properties.items() if info.get('type') == 'title']
        print(f"   - Title 속성: {title_props}")
        
        return True
        
    except Exception as e:
        print(f"❌ 노션 연결 실패: {e}")
        print(f"   에러 타입: {type(e).__name__}")
        return False

def test_page_creation():
    """테스트 페이지 생성"""
    print("\n3. 테스트 페이지 생성:")
    
    try:
        notion_secret = os.getenv('NOTION_INTEGRATION_SECRET')
        notion_db_id = os.getenv('NOTION_DATABASE_ID')
        
        # Mock 테스트 데이터
        class MockItem:
            def __init__(self):
                self.title = 'GitHub Actions Debug Test'
                self.summary = 'GitHub Actions에서 노션 연결 테스트'
                self.detailed_summary = 'GitHub Actions 워크플로우에서 노션 데이터베이스 연결이 정상적으로 작동하는지 확인하는 테스트입니다.'
                self.source = 'Debug Script'
                self.link = 'https://github.com/LimJih00n/ai-news-curator'
                self.importance_score = 3.0
                self.relevance_score = 5.0
        
        test_items = [MockItem()]
        
        sink = NotionSink(notion_secret, notion_db_id)
        sink.create_page('Debug Test - GitHub Actions', test_items)
        print("✅ 테스트 페이지 생성 성공!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 페이지 생성 실패: {e}")
        import traceback
        print(f"   스택 트레이스:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    connection_ok = debug_notion_connection()
    
    if connection_ok:
        test_page_creation()
    
    print("\n" + "=" * 50)
    print("🔧 디버깅 완료!")