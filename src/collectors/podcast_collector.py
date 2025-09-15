"""
Podcast Transcript 인사이트 수집기
- 주요 Tech/AI 팟캐스트의 핵심 인사이트 추출
- Transcript에서 실무 적용 가능한 정보 파싱
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
import feedparser
import requests
from dataclasses import dataclass
import re
import json
import os

@dataclass
class PodcastInsight:
    """팟캐스트 인사이트"""
    podcast_name: str
    episode_title: str
    guest: Optional[str]
    url: str
    published_at: datetime
    duration_minutes: int
    key_insights: List[str]  # 핵심 인사이트 3-5개
    mentioned_tools: List[str]  # 언급된 도구/프로젝트
    action_items: List[str]  # 실행 가능한 조언
    notable_quotes: List[str]  # 주목할 만한 인용구
    topics: List[str]
    summary: str  # 한글 요약

class PodcastCollector:
    """고품질 팟캐스트 인사이트 수집"""

    # 최고급 Tech/AI 팟캐스트
    PREMIUM_PODCASTS = {
        'deep_tech': [
            {
                'name': 'Lex Fridman Podcast',
                'rss': 'https://lexfridman.com/feed/podcast/',
                'focus': 'AI, Deep Learning, Philosophy',
                'quality': 10  # 최고 품질
            },
            {
                'name': 'The Robot Brains Podcast',
                'rss': 'https://feeds.transistor.fm/the-robot-brains',
                'focus': 'AI Research, Robotics',
                'quality': 9
            }
        ],

        'ai_engineering': [
            {
                'name': 'Latent Space',
                'rss': 'https://api.latent.space/feed/podcast',
                'focus': 'AI Engineering, LLMs in Production',
                'quality': 10
            },
            {
                'name': 'Practical AI',
                'rss': 'https://practicalai.fm/rss',
                'focus': 'Applied AI, Real-world ML',
                'quality': 8
            },
            {
                'name': 'TWIML AI Podcast',
                'rss': 'https://twimlai.com/feed',
                'focus': 'ML Research & Practice',
                'quality': 9
            }
        ],

        'tech_business': [
            {
                'name': 'All-In Podcast',
                'rss': 'https://feeds.megaphone.fm/all-in-with-chamath-jason-sacks-friedberg',
                'focus': 'Tech, Startups, VC, AI Impact',
                'quality': 9
            },
            {
                'name': 'Acquired',
                'rss': 'https://feeds.transistor.fm/acquired',
                'focus': 'Tech Company Deep Dives',
                'quality': 9
            }
        ],

        'developer': [
            {
                'name': 'The Changelog',
                'rss': 'https://changelog.com/podcast/feed',
                'focus': 'Open Source, Development',
                'quality': 8
            },
            {
                'name': 'Software Engineering Daily',
                'rss': 'https://softwareengineeringdaily.com/feed/podcast/',
                'focus': 'Software Architecture, Systems',
                'quality': 8
            }
        ]
    }

    # 인사이트 추출 패턴
    INSIGHT_PATTERNS = {
        'key_point': [
            r"the key (?:point|insight|takeaway) is",
            r"what's important is",
            r"the main thing is",
            r"fundamentally",
            r"at the end of the day"
        ],
        'prediction': [
            r"I (?:think|believe|predict)",
            r"in the next \d+ (?:years|months)",
            r"the future of",
            r"we're going to see",
            r"eventually"
        ],
        'action': [
            r"you should (?:try|do|consider)",
            r"my advice is",
            r"what works is",
            r"the trick is",
            r"pro tip"
        ]
    }

    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')

    def collect_recent_episodes(self, days_back: int = 7) -> List[PodcastInsight]:
        """최근 에피소드에서 인사이트 수집"""
        insights = []

        for category, podcasts in self.PREMIUM_PODCASTS.items():
            for podcast in podcasts:
                try:
                    # RSS 피드 파싱
                    feed = feedparser.parse(podcast['rss'])

                    for entry in feed.entries[:3]:  # 최근 3개 에피소드
                        # 날짜 확인
                        pub_date = datetime(*entry.published_parsed[:6])
                        if (datetime.now() - pub_date).days > days_back:
                            continue

                        # Transcript 가져오기 (있는 경우)
                        transcript = self._get_transcript(entry)

                        if transcript:
                            # 인사이트 추출
                            insight = self._extract_insights(
                                podcast['name'],
                                entry,
                                transcript,
                                podcast['focus']
                            )

                            if insight and len(insight.key_insights) > 0:
                                insights.append(insight)
                        else:
                            # Transcript 없으면 설명에서라도 추출
                            insight = self._extract_from_description(
                                podcast['name'],
                                entry,
                                podcast['focus']
                            )
                            if insight:
                                insights.append(insight)

                except Exception as e:
                    print(f"Error processing {podcast['name']}: {e}")
                    continue

        # 품질 점수로 정렬
        insights.sort(key=lambda x: len(x.key_insights), reverse=True)
        return insights

    def _extract_insights(self, podcast_name: str, entry: Dict,
                         transcript: str, focus: str) -> Optional[PodcastInsight]:
        """Transcript에서 인사이트 추출"""

        # GPT-4로 인사이트 추출 (비용 고려해서 요약본만)
        if self.openai_api_key and len(transcript) > 1000:
            insights_data = self._extract_with_gpt(transcript, focus)
        else:
            # 패턴 매칭으로 추출
            insights_data = self._extract_with_patterns(transcript)

        # 게스트 추출
        guest = self._extract_guest(entry.title, transcript)

        return PodcastInsight(
            podcast_name=podcast_name,
            episode_title=entry.title,
            guest=guest,
            url=entry.link,
            published_at=datetime(*entry.published_parsed[:6]),
            duration_minutes=self._extract_duration(entry),
            key_insights=insights_data.get('key_insights', []),
            mentioned_tools=insights_data.get('tools', []),
            action_items=insights_data.get('actions', []),
            notable_quotes=insights_data.get('quotes', []),
            topics=self._extract_topics(transcript),
            summary=self._generate_korean_summary(insights_data)
        )

    def _extract_with_gpt(self, transcript: str, focus: str) -> Dict:
        """GPT-4로 정교한 인사이트 추출"""
        import openai

        # Transcript 압축 (처음과 끝 부분 + 중요 부분)
        compressed = self._compress_transcript(transcript)

        prompt = f"""
        다음 {focus} 팟캐스트 transcript에서 핵심 정보를 추출하세요:

        {compressed[:3000]}

        추출할 정보:
        1. key_insights: 가장 중요한 인사이트 3-5개 (한 문장씩)
        2. tools: 언급된 도구/라이브러리/프로젝트 (이름만)
        3. actions: 즉시 실행 가능한 조언 2-3개
        4. quotes: 인상적인 인용구 2개

        JSON 형식으로 응답하세요.
        """

        try:
            client = openai.OpenAI(api_key=self.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-5-nano",  # 최신 고품질 모델
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            return json.loads(response.choices[0].message.content)
        except:
            return self._extract_with_patterns(transcript)

    def _extract_with_patterns(self, transcript: str) -> Dict:
        """패턴 매칭으로 인사이트 추출"""
        insights = {
            'key_insights': [],
            'tools': [],
            'actions': [],
            'quotes': []
        }

        lines = transcript.split('.')

        for line in lines:
            line_lower = line.lower().strip()

            # 핵심 포인트 찾기
            for pattern in self.INSIGHT_PATTERNS['key_point']:
                if re.search(pattern, line_lower):
                    insights['key_insights'].append(line.strip())
                    break

            # 액션 아이템 찾기
            for pattern in self.INSIGHT_PATTERNS['action']:
                if re.search(pattern, line_lower):
                    insights['actions'].append(line.strip())
                    break

            # 도구/프로젝트 찾기
            tools_pattern = r'\b(LangChain|OpenAI|Anthropic|Hugging Face|GitHub|Cursor|VS Code|PyTorch|TensorFlow|JAX|Docker|Kubernetes)\b'
            tools_found = re.findall(tools_pattern, line, re.IGNORECASE)
            insights['tools'].extend(tools_found)

        # 중복 제거
        insights['tools'] = list(set(insights['tools']))
        insights['key_insights'] = insights['key_insights'][:5]
        insights['actions'] = insights['actions'][:3]

        return insights

    def _compress_transcript(self, transcript: str) -> str:
        """긴 transcript를 중요 부분만 압축"""
        lines = transcript.split('.')

        # 중요도 점수 계산
        scored_lines = []
        for line in lines:
            score = 0
            line_lower = line.lower()

            # 중요 키워드 포함 시 점수 상승
            important_words = ['important', 'key', 'critical', 'fundamental',
                             'breakthrough', 'revolutionary', 'game-changer']
            score += sum(2 for word in important_words if word in line_lower)

            # 기술 용어 포함 시 점수 상승
            tech_words = ['AI', 'ML', 'LLM', 'GPT', 'model', 'training', 'data']
            score += sum(1 for word in tech_words if word.lower() in line_lower)

            scored_lines.append((score, line))

        # 점수 높은 순으로 정렬하고 상위 N개 선택
        scored_lines.sort(key=lambda x: x[0], reverse=True)

        important_lines = [line for score, line in scored_lines[:50]]
        return '. '.join(important_lines)

    def _extract_guest(self, title: str, transcript: str) -> Optional[str]:
        """게스트 이름 추출"""
        # 제목에서 "with {name}" 패턴 찾기
        match = re.search(r'with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', title)
        if match:
            return match.group(1)

        # Transcript 시작 부분에서 소개 찾기
        intro_pattern = r"(?:my guest today is|joining me today is|I'm talking to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        match = re.search(intro_pattern, transcript[:500], re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def _extract_duration(self, entry: Dict) -> int:
        """에피소드 길이 추출 (분)"""
        # iTunes duration 태그
        if hasattr(entry, 'itunes_duration'):
            duration = entry.itunes_duration
            if ':' in duration:
                parts = duration.split(':')
                if len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 60  # 기본값

    def _extract_topics(self, transcript: str) -> List[str]:
        """주요 토픽 추출"""
        topics = []

        # AI/ML 관련 토픽
        ai_topics = {
            'transformer': 'Transformer Models',
            'fine-tuning': 'Fine-tuning',
            'prompt engineering': 'Prompt Engineering',
            'rag': 'RAG (Retrieval Augmented Generation)',
            'agent': 'AI Agents',
            'multimodal': 'Multimodal AI',
            'embedding': 'Embeddings',
            'vector database': 'Vector Databases'
        }

        transcript_lower = transcript.lower()
        for keyword, topic in ai_topics.items():
            if keyword in transcript_lower:
                topics.append(topic)

        return topics[:5]

    def _generate_korean_summary(self, insights_data: Dict) -> str:
        """한글 요약 생성"""
        if not insights_data.get('key_insights'):
            return "핵심 인사이트를 추출할 수 없었습니다."

        # 첫 번째 인사이트를 한글로 간단 변환
        first_insight = insights_data['key_insights'][0]

        # 간단한 매핑 (실제로는 GPT 사용)
        if 'AI' in first_insight or 'LLM' in first_insight:
            return f"AI/LLM 관련 중요 인사이트: {len(insights_data['key_insights'])}개 발견"
        elif 'future' in first_insight.lower():
            return f"미래 전망 관련 인사이트 포함"
        else:
            return f"핵심 인사이트 {len(insights_data['key_insights'])}개와 실행 조언 {len(insights_data.get('actions', []))}개"

    def _get_transcript(self, entry: Dict) -> Optional[str]:
        """Transcript 가져오기 (YouTube는 자동 생성 자막 활용)"""
        # YouTube 링크인 경우
        if 'youtube.com' in entry.link or 'youtu.be' in entry.link:
            return self._get_youtube_transcript(entry.link)

        # Podcast 자체 transcript (일부만 제공)
        if hasattr(entry, 'content'):
            for content in entry.content:
                if content.type == 'text/plain':
                    return content.value

        return None

    def _get_youtube_transcript(self, url: str) -> Optional[str]:
        """YouTube 자동 생성 자막 가져오기"""
        # youtube-transcript-api 사용
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            # Video ID 추출
            video_id = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
            if video_id:
                video_id = video_id.group(1)
                transcript = YouTubeTranscriptApi.get_transcript(video_id)

                # 텍스트만 추출
                text = ' '.join([t['text'] for t in transcript])
                return text
        except:
            pass

        return None

    def _extract_from_description(self, podcast_name: str, entry: Dict, focus: str) -> Optional[PodcastInsight]:
        """설명에서라도 최소한의 정보 추출"""
        description = entry.get('summary', '') or entry.get('description', '')

        if len(description) < 100:
            return None

        # 설명에서 핵심 문장 추출
        sentences = description.split('.')
        key_insights = [s.strip() for s in sentences if len(s.strip()) > 50][:3]

        if not key_insights:
            return None

        return PodcastInsight(
            podcast_name=podcast_name,
            episode_title=entry.title,
            guest=self._extract_guest(entry.title, description),
            url=entry.link,
            published_at=datetime(*entry.published_parsed[:6]),
            duration_minutes=self._extract_duration(entry),
            key_insights=key_insights,
            mentioned_tools=[],
            action_items=[],
            notable_quotes=[],
            topics=self._extract_topics(description),
            summary=f"에피소드 설명에서 {len(key_insights)}개 포인트 추출"
        )


# 사용 예시
if __name__ == "__main__":
    import os

    collector = PodcastCollector(openai_api_key=os.getenv('OPENAI_API_KEY'))
    insights = collector.collect_recent_episodes(days_back=7)

    print(f"수집된 팟캐스트 인사이트: {len(insights)}개\n")

    for insight in insights[:3]:
        print(f"[{insight.podcast_name}]")
        print(f"제목: {insight.episode_title}")
        if insight.guest:
            print(f"게스트: {insight.guest}")
        print(f"길이: {insight.duration_minutes}분")
        print(f"핵심 인사이트:")
        for i, ki in enumerate(insight.key_insights[:3], 1):
            print(f"  {i}. {ki[:100]}...")
        if insight.mentioned_tools:
            print(f"언급된 도구: {', '.join(insight.mentioned_tools)}")
        print(f"URL: {insight.url}")
        print("-" * 50)