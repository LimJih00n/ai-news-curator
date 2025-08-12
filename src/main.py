from __future__ import annotations

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from src.config import load_config, validate_config
from src.source_loader import load_sources_config, get_all_feed_sources
from src.source_manager import HybridSourceManager, SourceConfig
from src.collectors.rss_collector import fetch_many
from src.collectors.arxiv_collector import query_arxiv
from src.collectors.youtube_collector import fetch_channel_latest_videos
from src.collectors.reddit_collector import RedditCollector
from src.collectors.yozm_collector import collect_latest_from_magazine
from src.collectors.content_filter import get_filtered_items
from src.output.md_note import write_daily_md
from src.sinks.notion_sink import NotionSink
from src.sinks.telegram_sink import TelegramSink
from src.parallel_summarizer import summarize_items_parallel
from src.cache_manager import content_cache
import time


def run_daily():
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    cfg = load_config()
    validate_config(cfg)
    
    # 하이브리드 소스 관리자 초기화 (Notion 우선, YAML 폴백)
    source_manager = HybridSourceManager(
        notion_secret=cfg.notion_source_secret,
        notion_db_id=cfg.notion_source_database_id
    )
    
    # 외부 소스에서 설정 로드
    external_sources = source_manager.get_all_sources()
    
    # 기존 YAML 소스도 로드 (폴백용)
    sources = load_sources_config()

    raw_items = fetch_many(cfg.rss_feeds)
    print(f"RSS collected: {len(raw_items)} items")
    
    # 외부 소스가 있으면 사용, 없으면 YAML 소스 사용
    if external_sources.get('website'):
        print(f"외부 소스 사용: {sum(len(v) for v in external_sources.values())}개 소스")
        # 웹사이트 및 뉴스레터 소스 수집
        for source in external_sources.get('website', []):
            try:
                items = fetch_many([source.url])
                raw_items.extend(items[:source.max_items])
                if items:
                    print(f"Added {len(items[:source.max_items])} items from {source.name}")
            except Exception as e:
                print(f"Failed to fetch {source.name}: {e}")
                continue
    else:
        # 기존 YAML 방식 폴백
        print("YAML 소스 사용 (외부 소스 없음)")
        all_feed_sources = get_all_feed_sources(sources)
        
        for source in all_feed_sources:
            try:
                items = fetch_many([source.url])
                # 각 소스별 지정된 개수만큼 추가
                raw_items.extend(items[:source.items_per_fetch])
                if items:
                    print(f"Added {len(items[:source.items_per_fetch])} items from {source.name}")
            except Exception as e:
                print(f"Failed to fetch {source.name}: {e}")
                continue
    
    if cfg.use_yozm_scraper:
        # Directly scrape Yozm magazine listing (non-RSS)
        yozm_items = collect_latest_from_magazine("https://yozm.wishket.com/magazine/", max_items=8)
        raw_items.extend(yozm_items)
        print(f"Yozm collected: {len(yozm_items)} items")
    
    # Google News RSS feeds (search-based) - sources.yaml에서 읽기
    if sources.google_news_queries:
        google_total = 0
        for query in sources.google_news_queries:
            google_news_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
            try:
                google_items = fetch_many([google_news_url])
                raw_items.extend(google_items[:5])  # Limit to 5 per query
                google_total += len(google_items[:5])
            except Exception:
                continue
        print(f"Google News collected: {google_total} items")
    
    # Reddit items (requires credentials)
    reddit_items_raw = []
    if cfg.reddit_client_id and cfg.reddit_client_secret and cfg.reddit_user_agent and cfg.reddit_subreddits:
        reddit_items_raw = RedditCollector(
            cfg.reddit_client_id, cfg.reddit_client_secret, cfg.reddit_user_agent
        ).fetch_top(cfg.reddit_subreddits, limit=10, time_filter="day")
    
    # arXiv items - sources.yaml의 쿼리 사용
    arxiv_items = query_arxiv(sources.arxiv_query, max_results=sources.arxiv_max_results)
    print(f"arXiv collected: {len(arxiv_items)} items")

    # 날짜 정렬 추가 - 최신순으로 정렬
    from datetime import datetime
    import dateutil.parser
    
    def get_item_date(item):
        """아이템의 날짜를 파싱하여 반환 (timezone-naive로 통일)"""
        try:
            if hasattr(item, 'published_at') and item.published_at:
                date_obj = item.published_at
                # timezone-aware면 naive로 변환
                if hasattr(date_obj, 'tzinfo') and date_obj.tzinfo is not None:
                    return date_obj.replace(tzinfo=None)
                return date_obj
            elif hasattr(item, 'published') and item.published:
                date_obj = dateutil.parser.parse(item.published)
                # timezone-aware면 naive로 변환
                if hasattr(date_obj, 'tzinfo') and date_obj.tzinfo is not None:
                    return date_obj.replace(tzinfo=None)
                return date_obj
            else:
                return datetime.min  # 날짜가 없으면 가장 오래된 것으로 취급
        except:
            return datetime.min
    
    # 모든 raw_items를 최신순으로 정렬
    raw_items.sort(key=get_item_date, reverse=True)
    print(f"최신순 정렬 완료: {len(raw_items)}개 항목")
    
    # AI 기반 필터링으로 상위 항목만 선별 - sources.yaml의 설정 사용
    print(f"AI 필터링 시작: {len(raw_items)}개 항목 중 상위 {sources.max_filtered_items}개 선별...")
    filtered_items = get_filtered_items(cfg.openai_api_key, raw_items, max_items=sources.max_filtered_items)
    
    # 선별된 항목들만 요약
    print(f"선별된 {len(filtered_items)}개 항목 요약 시작...")
    
    # 병렬 요약 처리 시작
    start_time = time.time()
    summarized_items = summarize_items_parallel(
        cfg.openai_api_key,
        filtered_items,
        max_workers=5  # 동시 처리할 워커 수
    )
    end_time = time.time()
    print(f"병렬 요약 완료: {end_time - start_time:.2f}초 소요")
    
    # arXiv 항목들도 병렬로 요약
    if arxiv_items:
        print(f"arXiv {len(arxiv_items)}개 항목 요약 시작...")
        arxiv_summarized = summarize_items_parallel(
            cfg.openai_api_key,
            arxiv_items[:10],  # 상위 10개만
            max_workers=3
        )
        summarized_items.extend(arxiv_summarized)
        print(f"arXiv 요약 완료: {len(arxiv_summarized)}개")
    
    # YouTube 채널에서 최신 영상 수집 및 요약
    youtube_items = []
    youtube_sources = external_sources.get('youtube', []) if external_sources.get('youtube') else sources.youtube_channels
    
    if youtube_sources:
        print(f"YouTube 채널에서 최신 영상 수집 시작...")
        if isinstance(youtube_sources[0], SourceConfig):
            # 외부 소스 (SourceConfig)
            channel_urls = [ch.url for ch in youtube_sources]
            max_videos = youtube_sources[0].max_items if youtube_sources else 2
        else:
            # YAML 소스
            channel_urls = [ch.url for ch in youtube_sources]
            max_videos = youtube_sources[0].max_videos if youtube_sources else 2
        
        youtube_items = fetch_channel_latest_videos(
            channel_urls=channel_urls,
            max_videos_per_channel=max_videos
        )
        print(f"YouTube 수집 완료: {len(youtube_items)}개 영상")
    
    if youtube_items:
        print(f"YouTube {len(youtube_items)}개 항목 요약 시작...")
        youtube_summarized = summarize_items_parallel(
            cfg.openai_api_key,
            youtube_items,
            max_workers=3
        )
        summarized_items.extend(youtube_summarized)
        print(f"YouTube 요약 완료: {len(youtube_summarized)}개")
    
    # 캐시 통계 출력
    cache_stats = content_cache.get_cache_stats()
    print(f"캐시 통계: {cache_stats}")
    
    print(f"총 요약 완료: {len(summarized_items)}개 항목")

    today = datetime.now().strftime("%Y-%m-%d")
    title = f"{cfg.daily_note_title_prefix} - {today}"
    md_path = os.path.join(cfg.output_dir, f"{title}.md")
    write_daily_md(md_path, title, summarized_items)

    if cfg.notion_secret and cfg.notion_database_id:
        try:
            print(f"🔍 Notion 업로드 시작...")
            print(f"   - Secret 길이: {len(cfg.notion_secret) if cfg.notion_secret else 0}")
            print(f"   - Database ID: {cfg.notion_database_id}")
            print(f"   - 요약 항목 수: {len(summarized_items)}")
            
            # 노션에는 상위 20개만 저장 (중요도순 정렬)
            notion_items = sorted(
                summarized_items, 
                key=lambda x: getattr(x, 'importance_score', 3.0), 
                reverse=True
            )[:20]
            
            print(f"   - Notion 저장 항목: 상위 {len(notion_items)}개 (중요도순)")
            
            notion_sink = NotionSink(cfg.notion_secret, cfg.notion_database_id)
            notion_sink.create_page(title, notion_items)
            print(f"✅ Notion 페이지 생성 완료: {title} (상위 {len(notion_items)}개 저장)")
        except Exception as e:
            print(f"❌ Notion 업로드 실패 (프로그램은 계속 실행됨): {e}")
            print(f"   에러 타입: {type(e).__name__}")
            print(f"   상세 메시지: {str(e)}")
            import traceback
            print(f"   스택 트레이스: {traceback.format_exc()}")
    else:
        print(f"⚠️ Notion 설정 누락:")
        print(f"   - NOTION_INTEGRATION_SECRET: {'✅' if cfg.notion_secret else '❌'}")
        print(f"   - NOTION_DATABASE_ID: {'✅' if cfg.notion_database_id else '❌'}")

    if cfg.telegram_bot_token and cfg.telegram_chat_id:
        # 노션 URL 생성 (데이터베이스 ID 기반)
        notion_url = None
        if cfg.notion_database_id:
            notion_url = f"https://glowing-eris-7ba.notion.site/{cfg.notion_database_id.replace('-', '')}?v={cfg.notion_database_id.replace('-', '')}8058b8af000cd51a681e&source=copy_link"
        
        # 중요도 순으로 정렬하여 상위 5개를 텔레그램으로 전송
        # importance_score가 높은 순으로 정렬 (중요도가 높은 것부터)
        telegram_items = sorted(
            summarized_items, 
            key=lambda x: getattr(x, 'importance_score', 3.0), 
            reverse=True
        )
        
        print(f"🚀 텔레그램 전송용 상위 5개 항목 (중요도순):")
        for i, item in enumerate(telegram_items[:5], 1):
            importance_score = getattr(item, 'importance_score', 3.0)
            stars = "⭐" * int(importance_score)
            print(f"   {i}. {stars} {item.title[:60]}... (중요도: {importance_score})")
        
        # 상위 5개만 간결한 형식으로 텔레그램 전송 (노션 링크 포함)
        TelegramSink(cfg.telegram_bot_token, cfg.telegram_chat_id).send_digest(title, telegram_items, max_items=5, notion_url=notion_url)


if __name__ == "__main__":
    run_daily()