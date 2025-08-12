from __future__ import annotations

from typing import List, Any, Union
from notion_client import Client
from src.models import ContentItem, ArxivItem, YoutubeItem
import re


class NotionSink:
    def __init__(self, integration_secret: str, database_id: str):
        self._client = Client(auth=integration_secret)
        # Notion API는 UUID 형식 (하이픈 포함)을 원함
        self._database_id = self._format_database_id(database_id)
        print(f"Notion database ID formatted: {self._database_id}")

    def _format_database_id(self, database_id: str) -> str:
        """데이터베이스 ID를 Notion API 형식으로 변환"""
        # 하이픈 제거
        clean_id = database_id.replace("-", "")
        
        # 32자리 문자열인지 확인
        if len(clean_id) == 32:
            # UUID 형식으로 변환: 8-4-4-4-12
            return f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
        
        # 이미 올바른 형식이거나 다른 형식이면 그대로 반환
        return database_id

    def create_page(self, title: str, items: List[Union[ContentItem, ArxivItem, YoutubeItem]]) -> None:
        """Notion 데이터베이스에 새 페이지 생성 (중복 체크)"""
        
        # 먼저 같은 제목의 페이지가 있는지 확인
        try:
            existing_pages = self._client.databases.query(
                database_id=self._database_id,
                filter={
                    "property": "Name",
                    "title": {
                        "equals": title
                    }
                }
            )
            
            # 이미 존재하는 페이지가 있으면 삭제
            if existing_pages and existing_pages.get('results'):
                for page in existing_pages['results']:
                    page_id = page['id']
                    print(f"Deleting existing page with title '{title}' (ID: {page_id})")
                    self._client.pages.update(
                        page_id=page_id,
                        archived=True  # Notion에서는 archived=True로 삭제
                    )
        except Exception as e:
            print(f"Warning: Could not check/delete existing pages: {e}")
            # 오류가 나도 계속 진행
        try:
            # 먼저 데이터베이스 구조 확인
            db_info = self._client.databases.retrieve(database_id=self._database_id)
            properties = db_info.get("properties", {})
            
            # 제목 속성 찾기 (Name, Title, 제목 등)
            title_property = None
            for prop_name, prop_info in properties.items():
                if prop_info.get("type") == "title":
                    title_property = prop_name
                    break
            
            if not title_property:
                print("Warning: No title property found in database")
                title_property = "Name"  # 기본값
            
            print(f"Using title property: {title_property}")
            
        except Exception as e:
            print(f"Could not retrieve database structure: {e}")
            print("Using default property name 'Name'")
            title_property = "Name"
        
        # 페이지 내용 생성
        children = []
        for item in items:
            # 제목
            item_title = getattr(item, 'title', 'Untitled')
            children.extend([
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": item_title[:2000]}}]  # 길이 제한
                    }
                },
            ])
            
            # 요약
            summary = getattr(item, 'summary', None)
            if summary:
                # Notion API는 2000자 제한이 있음
                if len(summary) > 2000:
                    summary_parts = [summary[i:i+2000] for i in range(0, len(summary), 2000)]
                    for part in summary_parts:
                        children.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": part}}]
                            }
                        })
                else:
                    children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": summary}}]
                        }
                    })
            
            # 소스 정보
            source = getattr(item, 'source', 'Unknown')
            
            # ArxivItem의 경우 저자 정보 추가
            if hasattr(item, 'authors') and item.authors:
                authors_text = f"Authors: {', '.join(item.authors[:5])}"  # 최대 5명
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": authors_text}}]
                    }
                })
            
            # YoutubeItem의 경우 채널 정보 추가
            if hasattr(item, 'channel') and item.channel:
                channel_text = f"Channel: {item.channel}"
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": channel_text}}]
                    }
                })
            
            # 소스
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "Source: "}},
                        {"type": "text", "text": {"content": source}, "annotations": {"italic": True}},
                    ]
                }
            })
            
            # 링크
            link = getattr(item, 'link', '')
            if link:
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "Read more: "}},
                            {"type": "text", "text": {"content": link, "link": {"url": link}}},
                        ]
                    }
                })
            
            # 구분선
            children.append({"object": "block", "type": "divider", "divider": {}})
        
        # 페이지 생성
        try:
            page_properties = {
                title_property: {"title": [{"text": {"content": title}}]},
            }
            
            response = self._client.pages.create(
                parent={"database_id": self._database_id},
                properties=page_properties,
                children=children[:100],  # Notion API는 최대 100개 블록 제한
            )
            print(f"✅ Successfully created Notion page: {title}")
            print(f"Page URL: {response.get('url', 'No URL returned')}")
            
        except Exception as e:
            print(f"❌ Failed to create Notion page: {e}")
            print(f"Database ID used: {self._database_id}")
            print("\n⚠️ Notion 연동 체크리스트:")
            print("1. Notion Integration이 생성되었는지 확인")
            print("2. Integration Secret이 올바른지 확인")
            print("3. 데이터베이스에 Integration이 연결되었는지 확인:")
            print("   - Notion에서 데이터베이스 페이지 열기")
            print("   - 우측 상단 '...' 메뉴 → 'Connections' → Integration 추가")
            print("4. 데이터베이스 ID가 올바른지 확인")
            raise