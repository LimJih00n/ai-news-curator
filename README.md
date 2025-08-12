# AI News Curator (MVP)

Pipeline integrating external repos ideas:
- RSS (GeekNews/요즘IT/AI Times) via `feedparser`
- arXiv Atom API
- OpenAI summarization
- Markdown daily note
- Optional Notion and Telegram sinks

## Setup
1. Create env
```bash
cp configs/.env.sample .env
```
Fill: `OPENAI_API_KEY` (required). Optional: Notion/Telegram/Reddit. Also set sources.

Required/optional envs:
- `OPENAI_API_KEY`
- `RSS_FEEDS` (comma-separated)
- `ARXIV_SEARCH_QUERY` (e.g., `cat:cs.AI`)
- `YOUTUBE_URLS` (comma-separated video URLs)
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` (optional)
- `REDDIT_SUBREDDITS` (comma-separated, e.g., `MachineLearning,ArtificialIntelligence`)
- `NOTION_INTEGRATION_SECRET`, `NOTION_DATABASE_ID` (optional)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (optional)
- `OUTPUT_DIR`, `DAILY_NOTE_TITLE_PREFIX`

2. Install deps
```bash
pip install -r requirements.txt
```

3. Run
```bash
python src/main.py
```
Outputs daily note under `output/notes/` and optionally posts to Notion/Telegram.

## Extend
- Add YouTube links to summarize: use `src/collectors/youtube_collector.py` to build `YoutubeItem` and pass transcript to summarizer.
- Reddit: fill credentials in `.env` and implement PRAW in `reddit_collector.py`.
