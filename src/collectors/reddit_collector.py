from __future__ import annotations

from dataclasses import dataclass
from typing import List
from datetime import datetime

import praw

from src.collectors.rss_collector import RawItem


class RedditCollector:
    def __init__(self, client_id: str | None = None, client_secret: str | None = None, user_agent: str | None = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self._reddit = None
        if client_id and client_secret and user_agent:
            self._reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
            )

    def fetch_top(self, subreddits: List[str], limit: int = 10, time_filter: str = "day") -> List[RawItem]:
        if not self._reddit or not subreddits:
            return []
        items: List[RawItem] = []
        for subreddit in subreddits:
            try:
                for submission in self._reddit.subreddit(subreddit).top(time_filter=time_filter, limit=limit):
                    published_iso = None
                    try:
                        published_iso = datetime.utcfromtimestamp(submission.created_utc).isoformat()
                    except Exception:
                        published_iso = None
                    content_text = submission.selftext if getattr(submission, "selftext", None) else None
                    items.append(
                        RawItem(
                            source=f"reddit/r/{subreddit}",
                            title=submission.title,
                            link=submission.url,
                            published=published_iso,
                            content=content_text,
                        )
                    )
            except Exception:
                continue
        return items
