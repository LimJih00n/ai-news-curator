#!/usr/bin/env python3
"""
Notion 소스 관리 데이터베이스 설정 스크립트
이 스크립트를 실행하여 Notion 데이터베이스를 설정하고 샘플 소스를 추가합니다.
"""

import os
import sys
from dotenv import load_dotenv
from src.source_manager import NotionSourceManager, SourceConfig, create_notion_source_database_template

def main():
    load_dotenv()
    
    # 환경 변수 확인
    notion_secret = os.getenv("NOTION_SOURCE_INTEGRATION_SECRET") or os.getenv("NOTION_INTEGRATION_SECRET")
    notion_db_id = os.getenv("NOTION_SOURCE_DATABASE_ID")
    
    if not notion_secret:
        print("❌ NOTION_SOURCE_INTEGRATION_SECRET 또는 NOTION_INTEGRATION_SECRET이 설정되지 않았습니다.")
        print("   .env 파일에 Notion Integration Secret을 추가해주세요.")
        return
    
    if not notion_db_id:
        print("❌ NOTION_SOURCE_DATABASE_ID가 설정되지 않았습니다.")
        print("\n📋 Notion 데이터베이스 설정 방법:")
        print("1. Notion에서 새 데이터베이스 페이지를 생성합니다")
        print("2. 데이터베이스 타입은 'Table'을 선택합니다")
        print("3. 다음 속성들을 추가합니다:")
        print()
        create_notion_source_database_template()
        print()
        print("4. 데이터베이스 URL에서 ID를 복사합니다:")
        print("   예: https://notion.so/workspace/24d6b8f0bbee80dcb749da270d6defcf?v=...")
        print("   위 URL에서 '24d6b8f0bbee80dcb749da270d6defcf'가 데이터베이스 ID입니다")
        print("5. .env 파일에 추가: NOTION_SOURCE_DATABASE_ID=24d6b8f0bbee80dcb749da270d6defcf")
        print("6. Integration을 데이터베이스에 연결합니다:")
        print("   - 데이터베이스 페이지 우측 상단 '...' 메뉴")
        print("   - 'Connections' 또는 '연결' 클릭")
        print("   - Integration 추가")
        return
    
    # Notion 관리자 초기화
    try:
        manager = NotionSourceManager(notion_secret, notion_db_id)
        print(f"✅ Notion 소스 관리자 초기화 성공")
        print(f"   Database ID: {notion_db_id}")
    except Exception as e:
        print(f"❌ Notion 연결 실패: {e}")
        return
    
    # 현재 소스 확인
    print("\n📊 현재 등록된 소스 확인 중...")
    existing_sources = manager.fetch_sources()
    
    if existing_sources:
        print(f"✅ {len(existing_sources)}개의 소스가 이미 등록되어 있습니다:")
        for source in existing_sources:
            print(f"   - {source.name} ({source.category}): {source.url}")
    else:
        print("📝 등록된 소스가 없습니다. 샘플 소스를 추가하시겠습니까? (y/n)")
        
        if input().lower() == 'y':
            # 샘플 소스 추가
            sample_sources = [
                # AI 연구 및 기술 블로그
                SourceConfig(
                    name="OpenAI Blog",
                    url="https://openai.com/blog/rss.xml",
                    category="website",
                    sub_category="ai_research",
                    max_items=3,
                    priority=9,
                    enabled=True
                ),
                SourceConfig(
                    name="Anthropic Blog",
                    url="https://blog.anthropic.com/rss.xml",
                    category="website",
                    sub_category="ai_research",
                    max_items=3,
                    priority=9,
                    enabled=True
                ),
                SourceConfig(
                    name="Google AI Blog",
                    url="https://ai.googleblog.com/atom.xml",
                    category="website",
                    sub_category="ai_research",
                    max_items=3,
                    priority=8,
                    enabled=True
                ),
                SourceConfig(
                    name="MIT Technology Review",
                    url="https://www.technologyreview.com/feed/",
                    category="website",
                    sub_category="tech_news",
                    max_items=3,
                    priority=7,
                    enabled=True
                ),
                
                # YouTube 채널
                SourceConfig(
                    name="Two Minute Papers",
                    url="https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg",
                    category="youtube",
                    sub_category="ai_research",
                    max_items=2,
                    priority=8,
                    enabled=True
                ),
                SourceConfig(
                    name="Lex Fridman",
                    url="https://www.youtube.com/feeds/videos.xml?channel_id=UCSHZKyawb77ixDdsGog4iWA",
                    category="youtube",
                    sub_category="ai_research",
                    max_items=1,
                    priority=7,
                    enabled=True
                ),
                
                # 뉴스레터
                SourceConfig(
                    name="The Batch by Andrew Ng",
                    url="https://www.deeplearning.ai/the-batch/feed",
                    category="newsletter",
                    sub_category="ai_research",
                    max_items=3,
                    priority=9,
                    enabled=True
                ),
                SourceConfig(
                    name="Import AI",
                    url="https://jack-clark.net/feed/",
                    category="newsletter",
                    sub_category="ai_research",
                    max_items=3,
                    priority=8,
                    enabled=True
                ),
            ]
            
            print(f"\n📝 {len(sample_sources)}개의 샘플 소스를 추가합니다...")
            
            success_count = 0
            for source in sample_sources:
                if manager.add_source(source):
                    success_count += 1
                    print(f"   ✅ {source.name} 추가 완료")
                else:
                    print(f"   ❌ {source.name} 추가 실패")
            
            print(f"\n✅ 총 {success_count}/{len(sample_sources)}개 소스가 추가되었습니다.")
    
    print("\n🎉 Notion 소스 관리 설정이 완료되었습니다!")
    print("   이제 main.py를 실행하면 Notion에서 소스를 동적으로 불러옵니다.")
    print("   Notion 데이터베이스에서 직접 소스를 추가/수정/삭제할 수 있습니다.")

if __name__ == "__main__":
    main()