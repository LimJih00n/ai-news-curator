#!/usr/bin/env python3
"""
Notion 데이터베이스 구조 확인 스크립트
"""

import os
from dotenv import load_dotenv
from src.source_manager import NotionSourceManager

def check_database_structure():
    load_dotenv()
    
    notion_secret = os.getenv("NOTION_SOURCE_INTEGRATION_SECRET") or os.getenv("NOTION_INTEGRATION_SECRET")
    notion_db_id = os.getenv("NOTION_SOURCE_DATABASE_ID")
    
    if not notion_secret or not notion_db_id:
        print("❌ Notion 설정이 완료되지 않았습니다.")
        return
    
    try:
        manager = NotionSourceManager(notion_secret, notion_db_id)
        
        # 데이터베이스 구조 확인
        db_info = manager.client.databases.retrieve(database_id=manager.database_id)
        properties = db_info.get("properties", {})
        
        print("🔍 현재 Notion 데이터베이스 속성들:")
        print(f"   데이터베이스 ID: {notion_db_id}")
        print(f"   총 {len(properties)}개 속성:")
        
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get("type", "unknown")
            print(f"   - {prop_name}: {prop_type}")
        
        # 필요한 속성들
        required_props = {
            "Name": "title",
            "URL": "url", 
            "Category": "select",
            "SubCategory": "select",
            "MaxItems": "number",
            "Priority": "number",
            "Enabled": "checkbox"
        }
        
        print("\\n📋 필요한 속성들 vs 현재 상태:")
        missing_props = []
        
        for prop_name, expected_type in required_props.items():
            if prop_name in properties:
                actual_type = properties[prop_name].get("type")
                status = "✅" if actual_type == expected_type else f"⚠️  (타입: {actual_type}, 예상: {expected_type})"
                print(f"   - {prop_name}: {status}")
            else:
                print(f"   - {prop_name}: ❌ 없음")
                missing_props.append(prop_name)
        
        if missing_props:
            print(f"\\n❌ {len(missing_props)}개 속성이 누락되었습니다:")
            for prop in missing_props:
                print(f"   - {prop} ({required_props[prop]})")
            
            print("\\n🔧 Notion에서 다음과 같이 속성을 추가해주세요:")
            print("1. Notion 데이터베이스 페이지로 이동")
            print("2. 테이블 헤더에서 '+' 버튼 클릭하여 속성 추가")
            
            for prop, prop_type in required_props.items():
                if prop in missing_props:
                    type_desc = {
                        "title": "제목",
                        "url": "URL",
                        "select": "선택",
                        "number": "숫자",
                        "checkbox": "체크박스"
                    }.get(prop_type, prop_type)
                    print(f"   - '{prop}' 속성을 '{type_desc}' 타입으로 추가")
        else:
            print("\\n✅ 모든 필요한 속성이 존재합니다!")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    check_database_structure()