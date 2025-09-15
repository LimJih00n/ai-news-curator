"""
무료 고품질 인사이트 수집기
- 유료 API 없이 고품질 인사이트 수집
- 실제로 접근 가능한 소스들 위주
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import feedparser
import requests
from dataclasses import dataclass
import re
from bs4 import BeautifulSoup
import json

@dataclass
class FreeInsight:
    """무료로 수집 가능한 인사이트"""
    source: str
    author: Optional[str]
    title: str
    content: str
    url: str
    published_at: datetime
    insight_type: str  # 'opinion', 'analysis', 'tutorial', 'research'
    topics: List[str]
    quality_score: float  # 0-10

class FreeInsightCollector:
    """유료 API 없이 고품질 인사이트 수집"""

    # 무료로 접근 가능한 고품질 소스들
    HIGH_QUALITY_SOURCES = {
        'substack': [
            {
                'name': 'The Pragmatic Engineer',
                'url': 'https://newsletter.pragmaticengineer.com/feed',
                'author': 'Gergely Orosz',
                'focus': 'Big Tech 내부 인사이트'
            },
            {
                'name': 'ByteByteGo',
                'url': 'https://blog.bytebytego.com/feed',
                'author': 'Alex Xu',
                'focus': '시스템 디자인'
            },
            {
                'name': 'TheSequence',
                'url': 'https://thesequence.substack.com/feed',
                'author': 'Jesus Rodriguez',
                'focus': 'AI/ML 실무'
            },
            {
                'name': 'AI Supremacy',
                'url': 'https://aisupremacy.substack.com/feed',
                'author': 'Michael Spencer',
                'focus': 'AI 트렌드 분석'
            }
        ],

        'tech_blogs': [
            {
                'name': 'Simon Willison Blog',
                'url': 'https://simonwillison.net/atom/everything/',
                'author': 'Simon Willison',
                'focus': 'LLM 도구, 실무 적용'
            },
            {
                'name': 'Lilian Weng Blog',
                'url': 'https://lilianweng.github.io/index.xml',
                'author': 'Lilian Weng (OpenAI)',
                'focus': 'ML 논문 리뷰'
            },
            {
                'name': 'Jay Alammar Blog',
                'url': 'https://jalammar.github.io/feed.xml',
                'author': 'Jay Alammar',
                'focus': 'ML 시각화 설명'
            },
            {
                'name': 'Chip Huyen Blog',
                'url': 'https://huyenchip.com/feed.xml',
                'author': 'Chip Huyen',
                'focus': 'MLOps, Production ML'
            }
        ],

        'hacker_news': [
            {
                'name': 'HN Best Comments',
                'url': 'https://hnrss.org/bestcomments',
                'focus': '고품질 기술 토론'
            },
            {
                'name': 'HN Front Page',
                'url': 'https://hnrss.org/frontpage',
                'focus': '핫 토픽'
            },
            {
                'name': 'HN Show',
                'url': 'https://hnrss.org/show',
                'focus': '신규 프로젝트'
            }
        ],

        'reddit': [
            {
                'name': 'r/LocalLLaMA Top',
                'url': 'https://www.reddit.com/r/LocalLLaMA/top/.rss?t=week',
                'focus': '로컬 LLM 실무'
            },
            {
                'name': 'r/MachineLearning Hot',
                'url': 'https://www.reddit.com/r/MachineLearning/hot/.rss',
                'focus': 'ML 연구 논의'
            },
            {
                'name': 'r/singularity',
                'url': 'https://www.reddit.com/r/singularity/hot/.rss',
                'focus': 'AGI 논의'
            }
        ],

        'github_discussions': [
            {
                'name': 'LangChain Discussions',
                'repo': 'langchain-ai/langchain',
                'focus': 'LLM 앱 개발'
            },
            {
                'name': 'AutoGPT Discussions',
                'repo': 'Significant-Gravitas/AutoGPT',
                'focus': 'AI Agent'
            },
            {
                'name': 'Ollama Discussions',
                'repo': 'ollama/ollama',
                'focus': '로컬 LLM'
            }
        ],

        'youtube_community': [
            # YouTube 커뮤니티 탭은 RSS 없지만 채널 자체 RSS는 가능
            {
                'name': 'Two Minute Papers',
                'channel_id': 'UCbfYPyITQ-7l4upoX8nvctg',
                'focus': 'AI 논문 리뷰'
            },
            {
                'name': 'Yannic Kilcher',
                'channel_id': 'UCZHmQk67mSJgfCCTn7xBfew',
                'focus': 'ML 논문 심화'
            }
        ],

        'mastodon': [
            # Mastodon은 오픈 소스라서 API 무료
            {
                'name': 'AI Researchers on Mastodon',
                'instance': 'sigmoid.social',
                'focus': 'AI 연구자 커뮤니티'
            }
        ]
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; AI-News-Curator/1.0)'
        })

    def collect_all_insights(self, hours_back: int = 24) -> List[FreeInsight]:
        """모든 무료 소스에서 인사이트 수집"""
        insights = []

        # 1. Substack 뉴스레터
        insights.extend(self._collect_substack(hours_back))

        # 2. 개인 기술 블로그
        insights.extend(self._collect_tech_blogs(hours_back))

        # 3. Hacker News 베스트
        insights.extend(self._collect_hackernews(hours_back))

        # 4. Reddit 인사이트
        insights.extend(self._collect_reddit(hours_back))

        # 5. GitHub Discussions (API 사용)
        insights.extend(self._collect_github_discussions(hours_back))

        # 6. YouTube RSS
        insights.extend(self._collect_youtube(hours_back))

        # 품질 점수로 정렬
        insights.sort(key=lambda x: x.quality_score, reverse=True)

        return insights

    def _collect_substack(self, hours_back: int) -> List[FreeInsight]:
        """Substack 뉴스레터 수집"""
        insights = []

        for newsletter in self.HIGH_QUALITY_SOURCES['substack']:
            try:
                feed = feedparser.parse(newsletter['url'])
                cutoff = datetime.now() - timedelta(hours=hours_back)

                for entry in feed.entries[:5]:
                    pub_date = datetime(*entry.published_parsed[:6])
                    if pub_date < cutoff:
                        continue

                    # 내용 파싱
                    content = self._clean_html(entry.summary if hasattr(entry, 'summary') else entry.description)

                    # Substack은 고품질이므로 높은 점수
                    insight = FreeInsight(
                        source=newsletter['name'],
                        author=newsletter['author'],
                        title=entry.title,
                        content=content[:1000],  # 처음 1000자
                        url=entry.link,
                        published_at=pub_date,
                        insight_type='analysis',
                        topics=self._extract_topics(entry.title + ' ' + content),
                        quality_score=8.5
                    )
                    insights.append(insight)

            except Exception as e:
                print(f"Error collecting from {newsletter['name']}: {e}")

        return insights

    def _collect_hackernews(self, hours_back: int) -> List[FreeInsight]:
        """Hacker News 베스트 댓글과 토론 수집"""
        insights = []

        # HN Best Comments는 정말 인사이트풀함
        try:
            feed = feedparser.parse('https://hnrss.org/bestcomments')
            cutoff = datetime.now() - timedelta(hours=hours_back)

            for entry in feed.entries[:10]:
                pub_date = datetime(*entry.published_parsed[:6])
                if pub_date < cutoff:
                    continue

                # HN 댓글은 짧지만 핵심적
                content = self._clean_html(entry.summary)

                # 댓글 작성자 추출
                author_match = re.search(r'by (\w+)', entry.title)
                author = author_match.group(1) if author_match else 'Unknown'

                insight = FreeInsight(
                    source='Hacker News Best',
                    author=author,
                    title=f"HN Comment: {entry.title[:100]}",
                    content=content,
                    url=entry.link,
                    published_at=pub_date,
                    insight_type='opinion',
                    topics=self._extract_topics(content),
                    quality_score=7.0  # HN 베스트 댓글은 고품질
                )
                insights.append(insight)

        except Exception as e:
            print(f"Error collecting HN: {e}")

        return insights

    def _collect_reddit(self, hours_back: int) -> List[FreeInsight]:
        """Reddit 고품질 포스트 수집"""
        insights = []

        for subreddit in self.HIGH_QUALITY_SOURCES['reddit']:
            try:
                feed = feedparser.parse(subreddit['url'])
                cutoff = datetime.now() - timedelta(hours=hours_back)

                for entry in feed.entries[:5]:
                    # Reddit 포스트 필터링 (높은 점수만)
                    content = self._clean_html(entry.summary)

                    # 업보트 수 추출 (제목에 있는 경우)
                    score_match = re.search(r'\[(\d+) points?\]', entry.title)
                    score = int(score_match.group(1)) if score_match else 0

                    # 높은 점수 포스트만
                    if score < 50:
                        continue

                    insight = FreeInsight(
                        source=subreddit['name'],
                        author=entry.author if hasattr(entry, 'author') else None,
                        title=entry.title,
                        content=content[:800],
                        url=entry.link,
                        published_at=datetime(*entry.published_parsed[:6]),
                        insight_type='discussion',
                        topics=self._extract_topics(entry.title + ' ' + content),
                        quality_score=min(9.0, 5.0 + score / 100)  # 점수 기반 품질
                    )
                    insights.append(insight)

            except Exception as e:
                print(f"Error collecting Reddit: {e}")

        return insights

    def _collect_github_discussions(self, hours_back: int) -> List[FreeInsight]:
        """GitHub Discussions 수집 (GraphQL API 사용)"""
        insights = []

        # GitHub API는 무료로 시간당 60개 요청 가능
        for repo_info in self.HIGH_QUALITY_SOURCES['github_discussions']:
            try:
                # GitHub API v3 사용 (더 간단)
                repo = repo_info['repo']
                url = f"https://api.github.com/repos/{repo}/discussions"

                response = self.session.get(url)
                if response.status_code == 200:
                    discussions = response.json()

                    for discussion in discussions[:3]:
                        # 최근 활발한 토론만
                        if discussion.get('comments', 0) < 5:
                            continue

                        insight = FreeInsight(
                            source=f"GitHub: {repo.split('/')[1]}",
                            author=discussion.get('user', {}).get('login'),
                            title=discussion.get('title', ''),
                            content=discussion.get('body', '')[:800],
                            url=discussion.get('html_url', ''),
                            published_at=datetime.fromisoformat(discussion.get('created_at', '').replace('Z', '')),
                            insight_type='discussion',
                            topics=[repo_info['focus']],
                            quality_score=6.5
                        )
                        insights.append(insight)

            except Exception as e:
                print(f"Error collecting GitHub: {e}")

        return insights

    def _collect_tech_blogs(self, hours_back: int) -> List[FreeInsight]:
        """개인 기술 블로그 수집"""
        insights = []

        for blog in self.HIGH_QUALITY_SOURCES['tech_blogs']:
            try:
                feed = feedparser.parse(blog['url'])
                cutoff = datetime.now() - timedelta(hours=hours_back * 24)  # 블로그는 더 긴 기간

                for entry in feed.entries[:3]:
                    pub_date = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now()
                    if pub_date < cutoff:
                        continue

                    content = self._clean_html(entry.summary if hasattr(entry, 'summary') else entry.description)

                    insight = FreeInsight(
                        source=blog['name'],
                        author=blog['author'],
                        title=entry.title,
                        content=content[:1500],
                        url=entry.link,
                        published_at=pub_date,
                        insight_type='analysis',
                        topics=self._extract_topics(entry.title + ' ' + content),
                        quality_score=9.0  # 개인 블로그는 보통 깊이 있음
                    )
                    insights.append(insight)

            except Exception as e:
                print(f"Error collecting blog {blog['name']}: {e}")

        return insights

    def _collect_youtube(self, hours_back: int) -> List[FreeInsight]:
        """YouTube 채널 RSS 수집"""
        insights = []

        for channel in self.HIGH_QUALITY_SOURCES['youtube_community']:
            try:
                # YouTube RSS URL
                rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel['channel_id']}"
                feed = feedparser.parse(rss_url)

                for entry in feed.entries[:3]:
                    pub_date = datetime(*entry.published_parsed[:6])

                    # YouTube 설명은 보통 짧음
                    description = entry.summary if hasattr(entry, 'summary') else ''

                    insight = FreeInsight(
                        source=f"YouTube: {channel['name']}",
                        author=channel['name'],
                        title=entry.title,
                        content=description,
                        url=entry.link,
                        published_at=pub_date,
                        insight_type='tutorial',
                        topics=[channel['focus']],
                        quality_score=7.5
                    )
                    insights.append(insight)

            except Exception as e:
                print(f"Error collecting YouTube: {e}")

        return insights

    def _clean_html(self, html_text: str) -> str:
        """HTML 태그 제거"""
        if not html_text:
            return ""

        # BeautifulSoup으로 깔끔하게 파싱
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            # 연속된 공백 제거
            text = ' '.join(text.split())
            return text
        except:
            # 실패시 간단한 정규식 사용
            text = re.sub(r'<[^>]+>', '', html_text)
            return ' '.join(text.split())

    def _extract_topics(self, text: str) -> List[str]:
        """텍스트에서 주제 추출"""
        topics = []
        text_lower = text.lower()

        # 주요 토픽 키워드
        topic_keywords = {
            'LLM': ['llm', 'large language model', 'gpt', 'claude', 'gemini'],
            'AI Agents': ['agent', 'autonomous', 'agentic'],
            'RAG': ['rag', 'retrieval', 'vector', 'embedding'],
            'Fine-tuning': ['fine-tun', 'finetun', 'lora', 'qlora'],
            'Multimodal': ['multimodal', 'vision', 'image', 'video'],
            'Code AI': ['copilot', 'cursor', 'code', 'programming'],
            'Local AI': ['local', 'on-device', 'edge', 'ollama'],
            'AI Safety': ['safety', 'alignment', 'ethics', 'bias']
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)

        return topics[:3]  # 최대 3개

    def get_top_insights(self, min_quality: float = 7.0) -> List[FreeInsight]:
        """고품질 인사이트만 필터링"""
        all_insights = self.collect_all_insights(hours_back=48)
        return [i for i in all_insights if i.quality_score >= min_quality]

    def get_discussions(self) -> List[FreeInsight]:
        """토론/논쟁 중심 인사이트"""
        all_insights = self.collect_all_insights(hours_back=24)
        return [i for i in all_insights if i.insight_type == 'discussion']

    def get_by_topic(self, topic: str) -> List[FreeInsight]:
        """특정 주제 인사이트"""
        all_insights = self.collect_all_insights(hours_back=72)
        return [i for i in all_insights if topic in i.topics]


# 사용 예시
if __name__ == "__main__":
    collector = FreeInsightCollector()

    print("🔍 무료 고품질 인사이트 수집 중...")
    insights = collector.get_top_insights(min_quality=7.0)

    print(f"\n✅ 수집 완료: {len(insights)}개 고품질 인사이트\n")

    for insight in insights[:5]:
        print(f"[{insight.quality_score:.1f}] {insight.source}")
        if insight.author:
            print(f"   저자: {insight.author}")
        print(f"   제목: {insight.title[:80]}")
        print(f"   주제: {', '.join(insight.topics)}")
        print(f"   내용: {insight.content[:150]}...")
        print(f"   URL: {insight.url}")
        print("-" * 60)