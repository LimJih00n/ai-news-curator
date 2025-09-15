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
from src.collectors.paper_collector import EnhancedPaperCollector, PaperEvaluator
# YouTube 수집기 제거됨
from src.collectors.reddit_collector import RedditCollector
from src.collectors.yozm_collector import collect_latest_from_magazine
from src.collectors.hackernews_collector import HackerNewsCollector
from src.collectors.producthunt_collector import ProductHuntCollector
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

    raw_items = []
    
    # Hacker News 전용 수집 (고품질 큐레이션)
    print("[HackerNews] 고품질 콘텐츠 수집 중...")
    hn_collector = HackerNewsCollector()
    hn_items = hn_collector.fetch_hybrid(
        top_limit=20,
        best_limit=5,
        show_limit=5,
        trending_hours=6
    )
    raw_items.extend(hn_items)
    print(f"Hacker News collected: {len(hn_items)} high-quality items")

    # Product Hunt 최신 제품 수집
    print("[ProductHunt] 최신 제품 수집 중...")
    ph_collector = ProductHuntCollector()
    ph_items = ph_collector.fetch_latest_products(limit=10)
    raw_items.extend(ph_items)
    print(f"Product Hunt collected: {len(ph_items)} products")
    
    # 기존 RSS 피드 수집 (HN RSS는 제외)
    rss_feeds = [feed for feed in cfg.rss_feeds if 'ycombinator' not in feed.lower()]
    rss_items = fetch_many(rss_feeds)
    raw_items.extend(rss_items)
    print(f"RSS collected: {len(rss_items)} items")
    
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
    
    # ========== 논문은 별도 트랙으로 처리 ==========
    print("\n" + "="*50)
    print("[PAPERS] 논문 수집 및 평가 (별도 트랙)")
    print("="*50)
    
    # 논문 수집 (개선된 collector 사용)
    paper_collector = EnhancedPaperCollector()
    papers = paper_collector.fetch_papers(
        query=None,  # 전체 카테고리 검색
        max_results=30,
        days_back=7  # 최근 7일
    )
    
    # 논문 평가 (논문 전용 기준)
    paper_evaluator = PaperEvaluator(cfg.openai_api_key)
    evaluated_papers = paper_evaluator.evaluate_papers(papers, max_papers=10)
    
    # 논문 요약 (학술적 스타일)
    paper_items = []
    for paper, score in evaluated_papers:
        paper.importance_score = score.overall_score
        paper.evaluation = score  # 평가 정보 저장
        paper_items.append(paper)
    
    print(f"[PAPERS] 최종 선별 논문: {len(paper_items)}개")
    
    # ========== 일반 뉴스는 기존대로 처리 ==========
    print("\n" + "="*50)
    print("[NEWS] 일반 뉴스 수집 및 평가")
    print("="*50)

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
    
    # 중복 제거 (개선된 알고리즘 사용)
    print(f"중복 제거 시작: {len(raw_items)}개 항목")
    raw_items = content_cache.deduplicate_items(raw_items, threshold=0.85)

    # 날짜 기반 필터링 - 오래된 뉴스 제거
    from datetime import timedelta
    cutoff_date = datetime.now() - timedelta(days=30)  # 30일 이상 오래된 뉴스 제거

    filtered_by_date = []
    old_items_count = 0

    for item in raw_items:
        item_date = get_item_date(item)
        if item_date > cutoff_date:
            filtered_by_date.append(item)
        else:
            old_items_count += 1

    if old_items_count > 0:
        print(f"오래된 뉴스 제거: {old_items_count}개 (30일 이상)")

    raw_items = filtered_by_date

    # 모든 raw_items를 최신순으로 정렬
    raw_items.sort(key=get_item_date, reverse=True)
    print(f"최신순 정렬 완료: {len(raw_items)}개 항목")
    
    # AI 기반 필터링으로 상위 항목만 선별 - OpenAI가 중요도 평가
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
    
    # 논문 요약 (별도 처리 - 학술적 스타일)
    if paper_items:
        print(f"\n[PAPERS] 논문 {len(paper_items)}개 요약 시작...")
        paper_summarized = summarize_items_parallel(
            cfg.openai_api_key,
            paper_items,
            max_workers=3
        )
        print(f"논문 요약 완료: {len(paper_summarized)}개")
    
    # ==== 블로그/Podcast 수집 추가 ====
    blog_items = []
    podcast_items = []

    # Free Insight Collector 사용 (고품질 블로그, GitHub 등)
    from src.collectors.free_insight_collector import FreeInsightCollector
    from src.models import ContentItem

    def convert_insight_to_contentitem(insight):
        """FreeInsight를 ContentItem으로 변환"""
        return ContentItem(
            source=insight.source,
            title=insight.title,
            link=insight.url,
            published_at=insight.published_at,
            raw_content=insight.content,
            tags=insight.topics
        )

    insight_collector = FreeInsightCollector()
    print(f"[BLOG] 고품질 블로그 내용 수집 시작...")
    try:
        insight_raw = insight_collector.collect_all_insights(hours_back=72)  # 3일치
        insight_items = [convert_insight_to_contentitem(item) for item in insight_raw[:10]]
        blog_items.extend(insight_items)
        print(f"[BLOG] Free Insight 수집 완료: {len(insight_items)}개")
    except Exception as e:
        print(f"[BLOG] Free Insight 수집 실패: {e}")
        insight_items = []

    # Podcast Collector 사용
    from src.collectors.podcast_collector import PodcastCollector

    def convert_podcast_to_contentitem(podcast):
        """PodcastInsight를 ContentItem으로 변환"""
        content = f"Episode: {podcast.episode_title}\n"
        if podcast.guest:
            content += f"Guest: {podcast.guest}\n"
        content += f"Duration: {podcast.duration_minutes} minutes\n\n"
        content += f"Summary: {podcast.summary}\n\n"
        content += "Key Insights:\n" + "\n".join([f"- {insight}" for insight in podcast.key_insights])

        return ContentItem(
            source=podcast.podcast_name,
            title=podcast.episode_title,
            link=podcast.url,
            published_at=podcast.published_at,
            raw_content=content,
            tags=podcast.topics
        )

    podcast_feeds = [
        "https://lexfridman.com/feed/podcast/",  # Lex Fridman Podcast
        "https://feeds.simplecast.com/BqbsxVfO",  # The TWIML AI Podcast
    ]

    podcast_collector = PodcastCollector()
    print(f"[PODCAST] 팟캐스트 수집 시작...")
    for feed_url in podcast_feeds:
        try:
            episodes_raw = podcast_collector.fetch_episodes(feed_url, max_episodes=2)
            episodes = [convert_podcast_to_contentitem(item) for item in episodes_raw]
            podcast_items.extend(episodes)
            if episodes:
                print(f"  수집됨: {len(episodes)}개 에피소드 from {feed_url[:30]}...")
        except Exception as e:
            print(f"  실패: {feed_url[:30]}... - {e}")
            continue

    print(f"[PODCAST] 팟캐스트 수집 완료: {len(podcast_items)}개")

    # 블로그/팟캐스트 요약
    additional_items = blog_items + podcast_items
    if additional_items:
        print(f"[SUMMARY] 추가 콘텐츠 {len(additional_items)}개 요약 시작...")
        additional_summarized = summarize_items_parallel(
            cfg.openai_api_key,
            additional_items,
            max_workers=3
        )
        summarized_items.extend(additional_summarized)
        print(f"[SUMMARY] 추가 콘텐츠 요약 완료: {len(additional_summarized)}개")
    
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
            print(f"\n[Notion] 업로드 시작...")
            
            # 뉴스와 논문 분리
            print(f"   - 뉴스: {len(summarized_items)}개")
            print(f"   - 논문: {len(paper_items)}개")
            
            # 뉴스 - 상위 15개 저장
            notion_news = sorted(
                summarized_items, 
                key=lambda x: getattr(x, 'importance_score', 3.0), 
                reverse=True
            )[:15]
            
            # 논문 - 상위 5개 저장
            notion_papers = paper_items[:5]
            
            # 뉴스와 논문을 합쳐서 전송 (이전 방식)
            all_notion_items = notion_news + notion_papers
            
            print(f"   - Notion 저장: 뉴스 {len(notion_news)}개 + 논문 {len(notion_papers)}개")
            
            notion_sink = NotionSink(cfg.notion_secret, cfg.notion_database_id)
            notion_sink.create_page_with_sections(title, notion_news, notion_papers)
            print(f"[OK] Notion 페이지 생성 완료: {title}")
        except Exception as e:
            print(f"[ERROR] Notion 업로드 실패: {e}")
    else:
        print(f"[WARNING] Notion 설정 누락:")
        print(f"   - NOTION_INTEGRATION_SECRET: {'OK' if cfg.notion_secret else 'MISSING'}")
        print(f"   - NOTION_DATABASE_ID: {'OK' if cfg.notion_database_id else 'MISSING'}")

    if cfg.telegram_bot_token and cfg.telegram_chat_id:
        # 노션 URL 생성
        notion_url = None
        if cfg.notion_database_id:
            notion_url = f"https://glowing-eris-7ba.notion.site/{cfg.notion_database_id.replace('-', '')}?v={cfg.notion_database_id.replace('-', '')}8058b8af000cd51a681e&source=copy_link"
        
        # 뉴스와 논문 각각 상위 선별
        top_news = sorted(
            summarized_items, 
            key=lambda x: getattr(x, 'importance_score', 3.0), 
            reverse=True
        )[:5]  # 뉴스 5개
        
        top_papers = paper_items[:3]  # 논문 3개
        
        print(f"\n[Telegram] 전송 준비:")
        print(f"   - 뉴스 TOP 5:")
        for i, item in enumerate(top_news, 1):
            score = getattr(item, 'importance_score', 3.0)
            print(f"     {i}. [{score:.1f}] {item.title[:50]}...")
        
        print(f"   - 논문 TOP 3:")
        for i, paper in enumerate(top_papers, 1):
            score = getattr(paper, 'importance_score', 5.0)
            print(f"     {i}. [{score:.1f}] {paper.title[:50]}...")
        
        # 통합 메시지 생성 (뉴스 + 논문)
        combined_items = []
        combined_items.append({"type": "header", "text": "[Today's AI News]"})
        combined_items.extend(top_news)
        combined_items.append({"type": "header", "text": "[Latest Papers]"})
        combined_items.extend(top_papers)
        
        # 텔레그램 전송
        TelegramSink(cfg.telegram_bot_token, cfg.telegram_chat_id).send_digest_separated(
            title, 
            news_items=top_news,
            paper_items=top_papers,
            notion_url=notion_url
        )


if __name__ == "__main__":
    run_daily()