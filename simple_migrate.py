#!/usr/bin/env python3
"""
현재 Notion DB 구조에 맞춰 간단하게 소스 이름만 추가
"""

import os
import yaml
from dotenv import load_dotenv
from notion_client import Client

def simple_migrate():
    load_dotenv()
    
    notion_secret = os.getenv("NOTION_SOURCE_INTEGRATION_SECRET") or os.getenv("NOTION_INTEGRATION_SECRET")
    notion_db_id = os.getenv("NOTION_SOURCE_DATABASE_ID")
    
    if not notion_secret or not notion_db_id:
        print("❌ Notion 설정이 완료되지 않았습니다.")
        return
    
    # Notion 클라이언트 초기화
    client = Client(auth=notion_secret)
    
    # 데이터베이스 ID 포맷
    if len(notion_db_id.replace('-', '')) == 32:
        clean_id = notion_db_id.replace('-', '')
        formatted_id = f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
    else:
        formatted_id = notion_db_id
    
    try:
        # YAML 파일 로드
        with open('configs/sources.yaml', 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        sources_to_add = []
        
        # 모든 소스들 수집
        categories = ['tech_news', 'ai_research', 'startup_innovation', 'academic_papers']
        
        for category in categories:
            for item in data.get(category, []):
                # 소스 정보를 이름에 포함
                name_with_info = f"{item['name']} | {item['url']} | {category} | max:{item.get('items_per_fetch', item.get('max_videos', 'N/A'))}"
                sources_to_add.append(name_with_info)
        
        # YouTube 채널들
        for item in data.get('youtube_channels', []):
            name_with_info = f"{item['name']} | {item['url']} | youtube | max:{item.get('max_videos', 2)}"
            sources_to_add.append(name_with_info)
        
        print(f"📝 총 {len(sources_to_add)}개 소스를 추가합니다...")
        
        success_count = 0
        failed_sources = []
        
        for name_with_info in sources_to_add:
            try:
                response = client.pages.create(
                    parent={"database_id": formatted_id},
                    properties={
                        "Name": {
                            "title": [{"text": {"content": name_with_info[:2000]}}]  # Notion 제한
                        }
                    }
                )
                success_count += 1
                source_name = name_with_info.split(' | ')[0]
                print(f"   ✅ {source_name}")
                
            except Exception as e:
                source_name = name_with_info.split(' | ')[0] 
                failed_sources.append(source_name)
                print(f"   ❌ {source_name}: {e}")
        
        print(f"\\n🎉 마이그레이션 완료!")
        print(f"   성공: {success_count}개")
        print(f"   실패: {len(failed_sources)}개")
        
        if failed_sources:
            print(f"\\n❌ 실패한 소스들:")
            for name in failed_sources:
                print(f"   - {name}")
        
        print(f"\\n📋 현재는 모든 정보가 Name 필드에 포함되어 있습니다.")
        print("나중에 다른 속성들을 추가한 후 데이터를 분리할 수 있습니다.")
        print(f"\\n🔗 Notion 데이터베이스: https://www.notion.so/{notion_db_id.replace('-', '')}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    simple_migrate()