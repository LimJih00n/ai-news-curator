#!/usr/bin/env python3
"""
YAML 소스를 Notion 데이터베이스로 마이그레이션하는 스크립트
"""

import os
import yaml
from dotenv import load_dotenv
from src.source_manager import NotionSourceManager, SourceConfig

def convert_youtube_url(url):
    """YouTube 채널 URL을 RSS 피드 URL로 변환"""
    # 현재는 채널 ID를 모르므로 원본 URL 반환 (수동으로 나중에 수정 필요)
    return url

def migrate_yaml_to_notion():
    load_dotenv()
    
    # 환경 변수 확인
    notion_secret = os.getenv("NOTION_SOURCE_INTEGRATION_SECRET") or os.getenv("NOTION_INTEGRATION_SECRET")
    notion_db_id = os.getenv("NOTION_SOURCE_DATABASE_ID")
    
    if not notion_secret or not notion_db_id:
        print("❌ Notion 설정이 완료되지 않았습니다.")
        print(f"NOTION_SECRET: {'✅' if notion_secret else '❌'}")
        print(f"NOTION_DATABASE_ID: {'✅' if notion_db_id else '❌'}")
        return
    
    try:
        # Notion 관리자 초기화
        manager = NotionSourceManager(notion_secret, notion_db_id)
        print(f"✅ Notion 연결 성공")
        
        # YAML 파일 로드
        with open('configs/sources.yaml', 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        sources_to_add = []
        
        # Tech News 소스들
        for item in data.get('tech_news', []):
            sources_to_add.append(SourceConfig(
                name=item['name'],
                url=item['url'],
                category='website',
                sub_category='tech_news',
                max_items=item['items_per_fetch'],
                priority=8 if 'MIT' in item['name'] or 'Hacker News' in item['name'] else 6,
                enabled=True
            ))
        
        # AI Research 소스들
        for item in data.get('ai_research', []):
            priority = 10 if 'OpenAI' in item['name'] or 'DeepMind' in item['name'] else \
                      9 if any(x in item['name'] for x in ['Google AI', 'Berkeley', 'MIT']) else \
                      8 if any(x in item['name'] for x in ['AWS', 'Microsoft', 'NVIDIA', 'Apple', 'Meta']) else 7
            
            sources_to_add.append(SourceConfig(
                name=item['name'],
                url=item['url'],
                category='website',
                sub_category='ai_research',
                max_items=item['items_per_fetch'],
                priority=priority,
                enabled=True
            ))
        
        # Startup Innovation 소스들
        for item in data.get('startup_innovation', []):
            priority = 9 if 'Y Combinator' in item['name'] else \
                      8 if any(x in item['name'] for x in ['Stratechery', 'Benedict Evans', 'Sequoia', 'First Round']) else 7
            
            category = 'newsletter' if 'Newsletter' in item['name'] or 'TLDR' in item['name'] else 'website'
            
            sources_to_add.append(SourceConfig(
                name=item['name'],
                url=item['url'],
                category=category,
                sub_category='startup',
                max_items=item['items_per_fetch'],
                priority=priority,
                enabled=True
            ))
        
        # Academic Papers 소스들
        for item in data.get('academic_papers', []):
            priority = 9 if 'Distill' in item['name'] else \
                      8 if any(x in item['name'] for x in ['arXiv AI', 'arXiv Machine Learning', 'arXiv NLP', 'arXiv Computer Vision', 'JMLR']) else 7
            
            sources_to_add.append(SourceConfig(
                name=item['name'],
                url=item['url'],
                category='arxiv' if 'arXiv' in item['name'] else 'website',
                sub_category='ai_research',
                max_items=item['items_per_fetch'],
                priority=priority,
                enabled=True
            ))
        
        # YouTube 채널들
        for item in data.get('youtube_channels', []):
            priority = 9 if 'Two Minute Papers' in item['name'] else \
                      8 if any(x in item['name'] for x in ['Fireship', 'AI Explained']) else 7
            
            sources_to_add.append(SourceConfig(
                name=item['name'],
                url=convert_youtube_url(item['url']),  # 나중에 수동으로 RSS URL로 변환 필요
                category='youtube',
                sub_category='ai_research' if 'AI' in item['name'] or 'Two Minute Papers' in item['name'] else 'tech_news',
                max_items=item['max_videos'],
                priority=priority,
                enabled=True
            ))
        
        print(f"\\n📝 총 {len(sources_to_add)}개 소스를 Notion에 추가합니다...")
        
        # 소스들을 Notion에 추가
        success_count = 0
        failed_sources = []
        
        for source in sources_to_add:
            try:
                if manager.add_source(source):
                    success_count += 1
                    print(f"   ✅ {source.name} ({source.category}) - 우선순위: {source.priority}")
                else:
                    failed_sources.append(source.name)
                    print(f"   ❌ {source.name} 추가 실패")
            except Exception as e:
                failed_sources.append(source.name)
                print(f"   ❌ {source.name} 추가 실패: {e}")
        
        print(f"\\n🎉 마이그레이션 완료!")
        print(f"   성공: {success_count}개")
        print(f"   실패: {len(failed_sources)}개")
        
        if failed_sources:
            print(f"\\n❌ 실패한 소스들:")
            for name in failed_sources:
                print(f"   - {name}")
        
        print(f"\\n📝 YouTube 채널 URL을 수동으로 RSS 피드 URL로 변환해야 합니다:")
        youtube_sources = [s for s in sources_to_add if s.category == 'youtube']
        for source in youtube_sources:
            print(f"   - {source.name}: {source.url}")
            print(f"     → RSS 형태로 변환 필요: https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID")
        
        print(f"\\n🔗 Notion 데이터베이스: https://www.notion.so/{notion_db_id.replace('-', '')}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    migrate_yaml_to_notion()