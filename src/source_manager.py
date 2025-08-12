"""
Notion 기반 외부 소스 관리 시스템
소스를 Notion 데이터베이스에서 관리하고 동적으로 불러오기
"""

from typing import List, Dict, Any, Optional
from notion_client import Client
from dataclasses import dataclass
import yaml
import json
from datetime import datetime
import os


@dataclass
class SourceConfig:
    """데이터 소스 설정"""
    name: str
    url: str
    category: str  # 'website', 'newsletter', 'youtube', 'twitter', 'threads'
    sub_category: Optional[str] = None  # 'ai_research', 'tech_news', 'startup' 등
    max_items: int = 5
    priority: int = 1  # 1-10, 높을수록 우선순위 높음
    enabled: bool = True
    added_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None


class NotionSourceManager:
    """Notion에서 소스를 관리하는 클래스"""
    
    def __init__(self, integration_secret: str, database_id: str):
        self.client = Client(auth=integration_secret)
        self.database_id = self._format_database_id(database_id)
        
    def _format_database_id(self, database_id: str) -> str:
        """데이터베이스 ID를 Notion API 형식으로 변환"""
        clean_id = database_id.replace("-", "")
        if len(clean_id) == 32:
            return f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
        return database_id
    
    def fetch_sources(self) -> List[SourceConfig]:
        """Notion 데이터베이스에서 모든 활성 소스 가져오기"""
        sources = []
        
        try:
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Enabled",
                    "checkbox": {
                        "equals": True
                    }
                }
            )
            
            for page in response.get('results', []):
                properties = page['properties']
                
                # 각 속성 추출
                name = self._get_text_property(properties, 'Name')
                url = self._get_url_property(properties, 'URL')
                category = self._get_select_property(properties, 'Category')
                sub_category = self._get_select_property(properties, 'SubCategory')
                max_items = self._get_number_property(properties, 'MaxItems', 5)
                priority = self._get_number_property(properties, 'Priority', 1)
                enabled = self._get_checkbox_property(properties, 'Enabled', True)
                
                if name and url and category:
                    sources.append(SourceConfig(
                        name=name,
                        url=url,
                        category=category,
                        sub_category=sub_category,
                        max_items=max_items,
                        priority=priority,
                        enabled=enabled,
                        added_date=datetime.now()
                    ))
                    
            print(f"Notion에서 {len(sources)}개 소스를 가져왔습니다.")
            return sources
            
        except Exception as e:
            print(f"Notion에서 소스를 가져오는 중 오류 발생: {e}")
            return []
    
    def add_source(self, source: SourceConfig) -> bool:
        """새로운 소스를 Notion 데이터베이스에 추가"""
        try:
            # 데이터베이스 구조를 확인하여 올바른 속성명 사용
            db_info = self.client.databases.retrieve(database_id=self.database_id)
            properties_info = db_info.get("properties", {})
            
            # Title 속성 찾기 (Name, NAME, Title 등)
            title_prop = None
            for prop_name, prop_data in properties_info.items():
                if prop_data.get("type") == "title":
                    title_prop = prop_name
                    break
            
            if not title_prop:
                title_prop = "NAME"  # 기본값
            
            self.client.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    title_prop: {"title": [{"text": {"content": source.name}}]},
                    "URL": {"url": source.url},
                    "Category": {"select": {"name": source.category}},
                    "SubCategory": {"select": {"name": source.sub_category or "General"}},
                    "MaxItems": {"number": source.max_items},
                    "Priority": {"number": source.priority},
                    "Enabled": {"checkbox": source.enabled}
                }
            )
            print(f"소스 '{source.name}'이(가) 추가되었습니다.")
            return True
            
        except Exception as e:
            print(f"소스 추가 중 오류 발생: {e}")
            return False
    
    def _get_text_property(self, properties: Dict, name: str, default: str = "") -> str:
        """텍스트 속성 추출 (대소문자 유연하게 처리)"""
        # 정확한 이름으로 먼저 시도
        prop = properties.get(name, {})
        if not prop:
            # 대소문자 다른 버전도 시도
            for prop_name in properties.keys():
                if prop_name.lower() == name.lower():
                    prop = properties[prop_name]
                    break
        
        if prop.get('title'):
            return prop['title'][0]['text']['content'] if prop['title'] else default
        elif prop.get('rich_text'):
            return prop['rich_text'][0]['text']['content'] if prop['rich_text'] else default
        return default
    
    def _get_url_property(self, properties: Dict, name: str, default: str = "") -> str:
        """URL 속성 추출"""
        prop = properties.get(name, {})
        return prop.get('url', default)
    
    def _get_select_property(self, properties: Dict, name: str, default: Optional[str] = None) -> Optional[str]:
        """Select 속성 추출"""
        prop = properties.get(name, {})
        select = prop.get('select', {})
        return select.get('name', default)
    
    def _get_number_property(self, properties: Dict, name: str, default: int = 0) -> int:
        """Number 속성 추출"""
        prop = properties.get(name, {})
        return int(prop.get('number', default))
    
    def _get_checkbox_property(self, properties: Dict, name: str, default: bool = False) -> bool:
        """Checkbox 속성 추출"""
        prop = properties.get(name, {})
        return prop.get('checkbox', default)


class HybridSourceManager:
    """Notion과 로컬 YAML을 모두 지원하는 하이브리드 소스 관리자"""
    
    def __init__(self, notion_secret: Optional[str] = None, notion_db_id: Optional[str] = None):
        self.notion_manager = None
        if notion_secret and notion_db_id:
            try:
                self.notion_manager = NotionSourceManager(notion_secret, notion_db_id)
                print("Notion 소스 관리자 초기화 성공")
            except Exception as e:
                print(f"Notion 소스 관리자 초기화 실패: {e}")
                print("로컬 YAML 파일을 사용합니다.")
    
    def get_all_sources(self) -> Dict[str, List[SourceConfig]]:
        """모든 소스를 카테고리별로 정리하여 반환"""
        sources_by_category = {
            'website': [],
            'newsletter': [],
            'youtube': [],
            'twitter': [],
            'threads': [],
            'arxiv': []
        }
        
        # 1. Notion에서 소스 가져오기 (가능한 경우)
        if self.notion_manager:
            try:
                notion_sources = self.notion_manager.fetch_sources()
                for source in notion_sources:
                    if source.category in sources_by_category:
                        sources_by_category[source.category].append(source)
                print(f"Notion에서 {len(notion_sources)}개 소스 로드")
            except Exception as e:
                print(f"Notion 소스 로드 실패: {e}")
        
        # 2. 로컬 YAML 파일에서 소스 가져오기 (폴백)
        if not self.notion_manager or all(len(v) == 0 for v in sources_by_category.values()):
            sources_by_category = self._load_from_yaml()
        
        # 3. 우선순위에 따라 정렬
        for category in sources_by_category:
            sources_by_category[category].sort(key=lambda x: x.priority, reverse=True)
        
        return sources_by_category
    
    def _load_from_yaml(self) -> Dict[str, List[SourceConfig]]:
        """기존 YAML 파일에서 소스 로드 (폴백)"""
        sources_by_category = {
            'website': [],
            'newsletter': [],
            'youtube': [],
            'twitter': [],
            'threads': [],
            'arxiv': []
        }
        
        yaml_path = 'configs/sources.yaml'
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
                # 웹사이트 및 뉴스레터
                for category in ['tech_news', 'ai_research', 'startup_innovation']:
                    if category in data:
                        for item in data[category]:
                            sources_by_category['website'].append(
                                SourceConfig(
                                    name=item['name'],
                                    url=item['url'],
                                    category='website',
                                    sub_category=category,
                                    max_items=item.get('items_per_fetch', 5),
                                    priority=5,
                                    enabled=True
                                )
                            )
                
                # YouTube 채널
                if 'youtube_channels' in data:
                    for item in data['youtube_channels']:
                        sources_by_category['youtube'].append(
                            SourceConfig(
                                name=item['name'],
                                url=item['url'],
                                category='youtube',
                                max_items=item.get('max_videos', 2),
                                priority=8,
                                enabled=True
                            )
                        )
                
                print(f"YAML에서 {sum(len(v) for v in sources_by_category.values())}개 소스 로드")
        
        return sources_by_category


def create_notion_source_database_template():
    """Notion 데이터베이스 템플릿 생성을 위한 속성 정의"""
    template = {
        "properties": {
            "Name": {"type": "title", "description": "소스 이름"},
            "URL": {"type": "url", "description": "소스 URL"},
            "Category": {
                "type": "select",
                "options": [
                    {"name": "website", "color": "blue"},
                    {"name": "newsletter", "color": "green"},
                    {"name": "youtube", "color": "red"},
                    {"name": "twitter", "color": "purple"},
                    {"name": "threads", "color": "orange"},
                    {"name": "arxiv", "color": "gray"}
                ]
            },
            "SubCategory": {
                "type": "select",
                "options": [
                    {"name": "ai_research", "color": "blue"},
                    {"name": "tech_news", "color": "green"},
                    {"name": "startup", "color": "yellow"},
                    {"name": "general", "color": "gray"}
                ]
            },
            "MaxItems": {"type": "number", "description": "최대 수집 개수"},
            "Priority": {"type": "number", "description": "우선순위 (1-10)"},
            "Enabled": {"type": "checkbox", "description": "활성화 여부"},
            "LastUpdated": {"type": "date", "description": "마지막 업데이트"},
            "Notes": {"type": "rich_text", "description": "메모"}
        }
    }
    
    print("Notion 데이터베이스에 다음 속성들을 생성하세요:")
    print(json.dumps(template, indent=2, ensure_ascii=False))
    return template