#!/usr/bin/env python3
"""
Notion API를 통해 데이터베이스 속성을 자동으로 추가하는 스크립트
"""

import os
from dotenv import load_dotenv
from notion_client import Client

def setup_database_properties():
    load_dotenv()
    
    notion_secret = os.getenv("NOTION_SOURCE_INTEGRATION_SECRET") or os.getenv("NOTION_INTEGRATION_SECRET")
    notion_db_id = os.getenv("NOTION_SOURCE_DATABASE_ID")
    
    if not notion_secret or not notion_db_id:
        print("❌ Notion 설정이 완료되지 않았습니다.")
        return
    
    client = Client(auth=notion_secret)
    
    # 데이터베이스 ID 포맷
    if len(notion_db_id.replace('-', '')) == 32:
        clean_id = notion_db_id.replace('-', '')
        formatted_id = f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
    else:
        formatted_id = notion_db_id
    
    # 추가할 속성들 정의
    properties_to_add = {
        "URL": {
            "type": "url"
        },
        "Category": {
            "type": "select",
            "select": {
                "options": [
                    {"name": "website", "color": "blue"},
                    {"name": "newsletter", "color": "green"},
                    {"name": "youtube", "color": "red"},
                    {"name": "blog", "color": "purple"},
                    {"name": "threads", "color": "orange"},
                    {"name": "arxiv", "color": "gray"}
                ]
            }
        },
        "SubCategory": {
            "type": "select",
            "select": {
                "options": [
                    {"name": "ai_research", "color": "blue"},
                    {"name": "tech_news", "color": "green"},
                    {"name": "startup", "color": "yellow"},
                    {"name": "general", "color": "gray"}
                ]
            }
        },
        "MaxItems": {
            "type": "number",
            "number": {
                "format": "number"
            }
        },
        "Priority": {
            "type": "number",
            "number": {
                "format": "number"
            }
        },
        "Enabled": {
            "type": "checkbox"
        }
    }
    
    try:
        print(f"🔧 Notion 데이터베이스에 속성들을 추가합니다...")
        print(f"   데이터베이스 ID: {formatted_id}")
        
        # 현재 데이터베이스 정보 가져오기
        current_db = client.databases.retrieve(database_id=formatted_id)
        current_properties = current_db.get("properties", {})
        
        print(f"\\n📋 현재 속성: {list(current_properties.keys())}")
        
        # 새로운 속성들을 기존 속성에 추가
        updated_properties = dict(current_properties)
        
        for prop_name, prop_config in properties_to_add.items():
            if prop_name not in current_properties:
                updated_properties[prop_name] = prop_config
                print(f"   + {prop_name} ({prop_config['type']}) 추가 예정")
            else:
                print(f"   ✅ {prop_name} 이미 존재")
        
        # 데이터베이스 업데이트
        response = client.databases.update(
            database_id=formatted_id,
            properties=updated_properties
        )
        
        print(f"\\n✅ 데이터베이스 속성 업데이트 완료!")
        
        # 업데이트된 속성 목록 확인
        updated_props = response.get("properties", {})
        print(f"\\n📊 업데이트된 속성 목록:")
        for prop_name, prop_info in updated_props.items():
            prop_type = prop_info.get("type", "unknown")
            print(f"   - {prop_name}: {prop_type}")
        
        print(f"\\n🎉 이제 소스 마이그레이션을 실행할 수 있습니다!")
        print("python3 migrate_sources_to_notion.py")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("\\n💡 Notion API로 데이터베이스 속성을 추가하려면:")
        print("1. Integration에 '데이터베이스 편집' 권한이 필요할 수 있습니다")
        print("2. 또는 수동으로 Notion에서 속성을 추가해주세요")

if __name__ == "__main__":
    setup_database_properties()