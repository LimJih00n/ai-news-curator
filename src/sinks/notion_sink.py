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
            print(f"🔍 데이터베이스 구조 확인 중... (ID: {self._database_id})")
            # 먼저 데이터베이스 구조 확인
            db_info = self._client.databases.retrieve(database_id=self._database_id)
            properties = db_info.get("properties", {})
            
            print(f"   - 데이터베이스 속성 개수: {len(properties)}")
            print(f"   - 속성 목록: {list(properties.keys())}")
            
            # 제목 속성 찾기 (Name, Title, 제목 등)
            title_property = None
            for prop_name, prop_info in properties.items():
                if prop_info.get("type") == "title":
                    title_property = prop_name
                    break
            
            if not title_property:
                print("⚠️ Warning: No title property found in database")
                title_property = "Name"  # 기본값
            
            print(f"✅ Title 속성 확인: {title_property}")
            
        except Exception as e:
            print(f"❌ 데이터베이스 구조 확인 실패: {e}")
            print(f"   에러 타입: {type(e).__name__}")
            print("   기본 속성명 'Name' 사용")
            title_property = "Name"
        
        # 페이지 내용 생성 (토글 형식으로 가독성 향상)
        children = []
        
        # 헤더 추가
        children.append({
            "object": "block",
            "type": "paragraph", 
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"📊 총 {len(items)}개 뉴스 | 중요도별 정렬 | "}, "annotations": {"bold": True}},
                    {"type": "text", "text": {"content": "토글을 클릭하여 상세 내용을 확인하세요"}, "annotations": {"italic": True}}
                ]
            }
        })
        
        children.append({"object": "block", "type": "divider", "divider": {}})
        
        for i, item in enumerate(items, 1):
            # 중요도와 한글 제목으로 토글 헤더 구성
            item_title = getattr(item, 'title', 'Untitled')
            summary = getattr(item, 'summary', '')
            importance_score = getattr(item, 'importance_score', 3.0)
            
            # 별점 생성
            stars = "⭐" * int(importance_score) if importance_score else "⭐⭐⭐"
            
            # 한글 요약을 토글 제목으로 사용 (더 길게)
            korean_title = summary[:50] + "..." if len(summary) > 50 else summary
            if not korean_title:
                korean_title = item_title[:50] + "..." if len(item_title) > 50 else item_title
            
            toggle_title = f"{stars} {i}. {korean_title}"
            
            # 토글 내용 구성
            toggle_children = []
            
            # 원제목 (영어)
            if item_title != korean_title:
                toggle_children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": item_title[:2000]}}]
                    }
                })
            
            # 상세 요약 (노션용)
            detailed_summary = getattr(item, 'detailed_summary', summary)
            if detailed_summary:
                # 상세 요약을 우선 표시
                if len(detailed_summary) > 2000:
                    summary_parts = [detailed_summary[i:i+2000] for i in range(0, len(detailed_summary), 2000)]
                    for part in summary_parts:
                        toggle_children.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": part}}]
                            }
                        })
                else:
                    toggle_children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": detailed_summary}}]
                        }
                    })
                
                # 한줄 요약도 별도로 표시 (구분을 위해)
                if summary != detailed_summary and summary:
                    toggle_children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": "📝 한줄 요약: "}, "annotations": {"bold": True}},
                                {"type": "text", "text": {"content": summary}, "annotations": {"color": "gray"}}
                            ]
                        }
                    })
            
            # 메타 정보 섹션
            meta_info = []
            
            # 중요도 점수
            if hasattr(item, 'importance_score'):
                meta_info.append(f"중요도: {stars} ({importance_score}/5)")
                
            if hasattr(item, 'relevance_score'):
                meta_info.append(f"관련성: {getattr(item, 'relevance_score', 0)}/10")
            
            # 소스 정보
            source = getattr(item, 'source', 'Unknown')
            meta_info.append(f"출처: {source}")
            
            # ArxivItem의 경우 저자 정보
            if hasattr(item, 'authors') and item.authors:
                authors_text = f"저자: {', '.join(item.authors[:3])}"
                if len(item.authors) > 3:
                    authors_text += f" 외 {len(item.authors)-3}명"
                meta_info.append(authors_text)
            
            # YoutubeItem의 경우 채널 정보
            if hasattr(item, 'channel') and item.channel:
                meta_info.append(f"채널: {item.channel}")
            
            # 메타 정보를 하나의 단락으로 구성
            if meta_info:
                meta_text = " | ".join(meta_info)
                toggle_children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": meta_text}, "annotations": {"color": "gray"}}]
                    }
                })
            
            # 원문 링크
            link = getattr(item, 'link', '')
            if link:
                toggle_children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "🔗 원문 보기: "}},
                            {"type": "text", "text": {"content": link, "link": {"url": link}}, "annotations": {"underline": True}},
                        ]
                    }
                })
            
            # 토글 블록 생성
            children.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": toggle_title}}],
                    "children": toggle_children
                }
            })
        
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