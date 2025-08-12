import os
from dataclasses import dataclass
from typing import List


def _split_csv(value: str) -> List[str]:
    return [v.strip() for v in value.split(",") if v.strip()] if value else []


@dataclass
class AppConfig:
    openai_api_key: str

    notion_secret: str | None
    notion_database_id: str | None
    
    # Notion 소스 관리용 설정
    notion_source_database_id: str | None
    notion_source_secret: str | None

    telegram_bot_token: str | None
    telegram_chat_id: str | None

    youtube_api_key: str | None
    reddit_client_id: str | None
    reddit_client_secret: str | None
    reddit_user_agent: str | None
    reddit_subreddits: List[str]
    arxiv_query: str
    rss_feeds: List[str]

    timezone: str
    output_dir: str
    daily_note_title_prefix: str
    youtube_urls: List[str]
    use_yozm_scraper: bool
    google_news_queries: List[str]
    max_filtered_items: int
    # 병렬 처리 설정
    max_workers: int
    enable_cache: bool
    cache_ttl_days: int


def load_config() -> AppConfig:
    return AppConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        notion_secret=os.getenv("NOTION_INTEGRATION_SECRET"),
        notion_database_id=os.getenv("NOTION_DATABASE_ID"),
        notion_source_database_id=os.getenv("NOTION_SOURCE_DATABASE_ID"),
        notion_source_secret=os.getenv("NOTION_SOURCE_INTEGRATION_SECRET") or os.getenv("NOTION_INTEGRATION_SECRET"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        youtube_api_key=os.getenv("YOUTUBE_API_KEY"),
        reddit_client_id=os.getenv("REDDIT_CLIENT_ID"),
        reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        reddit_user_agent=os.getenv("REDDIT_USER_AGENT"),
        reddit_subreddits=_split_csv(os.getenv("REDDIT_SUBREDDITS", "")),
        arxiv_query=os.getenv("ARXIV_SEARCH_QUERY", "cat:cs.AI"),
        rss_feeds=_split_csv(os.getenv("RSS_FEEDS", "")),
        timezone=os.getenv("TIMEZONE", "Asia/Seoul"),
        output_dir=os.getenv("OUTPUT_DIR", "./output/notes"),
        daily_note_title_prefix=os.getenv("DAILY_NOTE_TITLE_PREFIX", "AI-IT-Digest"),
        youtube_urls=_split_csv(os.getenv("YOUTUBE_URLS", "")),
        use_yozm_scraper=os.getenv("USE_YOZM_SCRAPER", "false").lower() in {"1", "true", "yes", "y"},
        google_news_queries=_split_csv(os.getenv("GOOGLE_NEWS_QUERIES", "")),
        max_filtered_items=int(os.getenv("MAX_FILTERED_ITEMS", "100")),
        max_workers=int(os.getenv("MAX_WORKERS", "4")),
        enable_cache=os.getenv("ENABLE_CACHE", "false").lower() in {"1", "true", "yes", "y"},
        cache_ttl_days=int(os.getenv("CACHE_TTL_DAYS", "7")),
    )


def validate_config(cfg: AppConfig) -> None:
    if not cfg.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required")
