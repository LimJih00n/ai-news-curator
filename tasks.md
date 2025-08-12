# AI News Curator - Tasks

- [x] Initialize project skeleton (dirs, basic files)
- [x] Define .env template and config loader
- [x] Implement RSS collector (GeekNews, 요즘IT, AI Times)
- [x] Implement arXiv collector (query + categories)
- [x] Implement YouTube collector (channels/playlists captions)
- [ ] Implement Reddit collector (subreddits, search)
- [x] Implement LLM summarizer (OpenAI)
- [x] Define unified schema for items (title, link, source, date, content, summary, tags)
- [x] Implement MD note generator (daily note)
- [x] Implement Notion sink (append to database/page)
- [x] Implement Telegram sink (channel/DM alerts)
- [x] Add CLI entry (daily run, source toggles)
- [ ] Add scheduler (cron/systemd or GitHub Actions)
- [ ] Add logging & error handling
- [ ] Add unit tests for core modules
- [ ] Dry-run with sample sources
- [ ] Document setup & usage (README)

## External repos to reuse
- [x] Clone references: AI-News-Aggregator, summary-gpt-bot, ai-summarizer-telegram-bot, youtube-summarizer, arxiv-sanity-bot, RSS2Telegram
- [x] Reuse Notion integration patterns from AI-News-Aggregator
- [x] Reuse Telegram bot command/handlers from summary-gpt-bot/RSS2Telegram
- [x] Reuse arXiv query logic from arxiv-sanity-bot
- [x] Reuse YouTube caption fetch flow from youtube-summarizer
