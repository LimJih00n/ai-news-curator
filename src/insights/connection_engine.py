"""
인사이트 연결 엔진
- 서로 다른 소스의 정보를 연결해서 새로운 인사이트 도출
- 트렌드, 논쟁, 기회 발견
"""

from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import networkx as nx
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

@dataclass
class ConnectedInsight:
    """연결된 인사이트"""
    title: str
    insight_type: str  # 'trend', 'debate', 'opportunity', 'pattern'
    connected_items: List[Dict]  # 연결된 원본 아이템들
    connection_reason: str  # 연결 이유
    synthesis: str  # 종합된 인사이트
    confidence: float  # 0-1, 연결 신뢰도
    action_items: List[str]  # 실행 가능한 조언
    timeline: Optional[str]  # 시간적 맥락

class InsightConnectionEngine:
    """정보 간 연결점을 찾아 인사이트 도출"""

    def __init__(self):
        self.graph = nx.Graph()  # 지식 그래프
        self.vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
        self.item_embeddings = {}  # 아이템별 임베딩 캐시

    def find_connections(self, items: List[Dict]) -> List[ConnectedInsight]:
        """아이템 간 연결점 찾기"""
        insights = []

        # 1. 그래프 구축
        self._build_knowledge_graph(items)

        # 2. 다양한 연결 패턴 탐색
        insights.extend(self._find_trends(items))
        insights.extend(self._find_debates(items))
        insights.extend(self._find_opportunities(items))
        insights.extend(self._find_temporal_patterns(items))

        # 3. 신뢰도 순으로 정렬
        insights.sort(key=lambda x: x.confidence, reverse=True)

        return insights[:10]  # 상위 10개

    def _build_knowledge_graph(self, items: List[Dict]):
        """지식 그래프 구축"""
        # 노드 추가
        for i, item in enumerate(items):
            self.graph.add_node(
                i,
                title=item.get('title', ''),
                source=item.get('source', ''),
                date=item.get('published_at'),
                content=self._get_content(item)
            )

        # 엣지 추가 (유사도 기반)
        contents = [self._get_content(item) for item in items]
        if len(contents) > 1:
            # TF-IDF 벡터화
            try:
                embeddings = self.vectorizer.fit_transform(contents)
                similarities = cosine_similarity(embeddings)

                # 임계값 이상의 유사도를 가진 아이템끼리 연결
                threshold = 0.3
                for i in range(len(items)):
                    for j in range(i + 1, len(items)):
                        sim = similarities[i, j]
                        if sim > threshold:
                            self.graph.add_edge(i, j, weight=sim)
            except:
                pass

    def _find_trends(self, items: List[Dict]) -> List[ConnectedInsight]:
        """트렌드 패턴 발견"""
        trends = []

        # 주제별 그룹화
        topic_groups = self._group_by_topics(items)

        for topic, group_items in topic_groups.items():
            if len(group_items) >= 3:  # 3개 이상 모이면 트렌드
                # 시간 순 정렬
                group_items.sort(key=lambda x: x.get('published_at', datetime.min))

                # 트렌드 방향 분석
                direction = self._analyze_trend_direction(group_items)

                insight = ConnectedInsight(
                    title=f"📈 Emerging Trend: {topic}",
                    insight_type='trend',
                    connected_items=group_items[:5],
                    connection_reason=f"{len(group_items)}개 소스에서 동시에 다루는 주제",
                    synthesis=self._synthesize_trend(topic, group_items, direction),
                    confidence=min(0.9, len(group_items) / 10),
                    action_items=self._generate_trend_actions(topic, direction),
                    timeline=self._get_timeline(group_items)
                )
                trends.append(insight)

        return trends

    def _find_debates(self, items: List[Dict]) -> List[ConnectedInsight]:
        """논쟁/상반된 의견 발견"""
        debates = []

        # 감성 분석으로 같은 주제에 대한 상반된 의견 찾기
        topic_sentiments = defaultdict(lambda: {'positive': [], 'negative': []})

        for item in items:
            topics = self._extract_topics(item)
            sentiment = self._analyze_sentiment(item)

            for topic in topics:
                if sentiment == 'positive':
                    topic_sentiments[topic]['positive'].append(item)
                elif sentiment == 'negative':
                    topic_sentiments[topic]['negative'].append(item)

        # 찬반이 모두 있는 주제 추출
        for topic, sentiments in topic_sentiments.items():
            if sentiments['positive'] and sentiments['negative']:
                all_items = sentiments['positive'][:2] + sentiments['negative'][:2]

                insight = ConnectedInsight(
                    title=f"⚔️ Debate: {topic}",
                    insight_type='debate',
                    connected_items=all_items,
                    connection_reason="같은 주제에 대한 상반된 관점",
                    synthesis=self._synthesize_debate(topic, sentiments),
                    confidence=0.7,
                    action_items=[
                        f"양쪽 관점 모두 검토 필요",
                        f"실무 적용 시 리스크 고려"
                    ],
                    timeline=None
                )
                debates.append(insight)

        return debates

    def _find_opportunities(self, items: List[Dict]) -> List[ConnectedInsight]:
        """기회 발견 (gap, unmet needs)"""
        opportunities = []

        # 1. 문제 언급 + 해결책 부재
        problems = self._find_problems(items)
        solutions = self._find_solutions(items)

        unmet_problems = self._find_unmet_needs(problems, solutions)
        for problem in unmet_problems:
            insight = ConnectedInsight(
                title=f"💡 Opportunity: {problem['topic']}",
                insight_type='opportunity',
                connected_items=problem['items'],
                connection_reason="여러 곳에서 언급되는 미해결 문제",
                synthesis=f"'{problem['topic']}'에 대한 해결책이 필요함. {len(problem['items'])}개 소스에서 문제 제기",
                confidence=0.6,
                action_items=[
                    f"{problem['topic']} 해결 방안 연구",
                    "프로토타입 개발 고려"
                ],
                timeline=None
            )
            opportunities.append(insight)

        # 2. 신기술 + 적용 분야
        new_tech = self._find_new_technologies(items)
        for tech in new_tech:
            applications = self._suggest_applications(tech)
            if applications:
                insight = ConnectedInsight(
                    title=f"🚀 Application Opportunity: {tech['name']}",
                    insight_type='opportunity',
                    connected_items=tech['items'],
                    connection_reason="새로운 기술의 적용 가능 분야",
                    synthesis=f"{tech['name']}을(를) {', '.join(applications)}에 적용 가능",
                    confidence=0.5,
                    action_items=applications[:3],
                    timeline="3-6개월 내 적용 가능"
                )
                opportunities.append(insight)

        return opportunities

    def _find_temporal_patterns(self, items: List[Dict]) -> List[ConnectedInsight]:
        """시간적 패턴 발견 (발전, 진화)"""
        patterns = []

        # 같은 주제의 시간적 변화 추적
        topic_timeline = defaultdict(list)

        for item in items:
            topics = self._extract_topics(item)
            date = item.get('published_at', datetime.min)

            for topic in topics:
                topic_timeline[topic].append((date, item))

        for topic, timeline in topic_timeline.items():
            if len(timeline) >= 3:
                # 시간순 정렬
                timeline.sort(key=lambda x: x[0])

                # 진화 패턴 분석
                evolution = self._analyze_evolution(timeline)

                if evolution:
                    insight = ConnectedInsight(
                        title=f"🔄 Evolution: {topic}",
                        insight_type='pattern',
                        connected_items=[item for _, item in timeline[:5]],
                        connection_reason="시간에 따른 발전 패턴",
                        synthesis=evolution,
                        confidence=0.7,
                        action_items=[
                            "다음 단계 예측 및 준비",
                            "현재 단계 최적화"
                        ],
                        timeline=self._format_timeline(timeline)
                    )
                    patterns.append(insight)

        return patterns

    def _group_by_topics(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """주제별로 아이템 그룹화"""
        topic_groups = defaultdict(list)

        for item in items:
            topics = self._extract_topics(item)
            for topic in topics:
                topic_groups[topic].append(item)

        return dict(topic_groups)

    def _extract_topics(self, item: Dict) -> List[str]:
        """아이템에서 주제 추출"""
        topics = []

        # 제목과 내용에서 키워드 추출
        text = f"{item.get('title', '')} {self._get_content(item)}"

        # 주요 키워드
        keywords = [
            'LLM', 'GPT', 'Claude', 'AI Agent', 'RAG', 'Fine-tuning',
            'Multimodal', 'Code Generation', 'Prompt Engineering',
            'Vector Database', 'Embedding', 'Transformer',
            'On-device AI', 'AI Safety', 'AGI'
        ]

        for keyword in keywords:
            if keyword.lower() in text.lower():
                topics.append(keyword)

        # 명시적 토픽 필드가 있으면 추가
        if 'topics' in item:
            topics.extend(item['topics'])

        return list(set(topics))[:3]  # 최대 3개

    def _analyze_sentiment(self, item: Dict) -> str:
        """감성 분석"""
        text = self._get_content(item).lower()

        positive_words = ['breakthrough', 'amazing', 'revolutionary', 'excellent', 'success']
        negative_words = ['problem', 'issue', 'failure', 'concern', 'limitation']

        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)

        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        return 'neutral'

    def _get_content(self, item: Dict) -> str:
        """아이템의 텍스트 콘텐츠 추출"""
        content_fields = ['content', 'summary', 'raw_content', 'description', 'abstract']
        for field in content_fields:
            if field in item and item[field]:
                return str(item[field])
        return item.get('title', '')

    def _analyze_trend_direction(self, items: List[Dict]) -> str:
        """트렌드 방향 분석"""
        # 시간에 따른 언급 빈도, 감성 변화 등 분석
        recent_sentiment = self._analyze_sentiment(items[-1]) if items else 'neutral'

        if recent_sentiment == 'positive':
            return 'rising'
        elif recent_sentiment == 'negative':
            return 'declining'
        return 'stable'

    def _synthesize_trend(self, topic: str, items: List[Dict], direction: str) -> str:
        """트렌드 종합"""
        sources = list(set([item.get('source', 'Unknown') for item in items[:5]]))
        source_str = ', '.join(sources[:3])

        direction_kr = {'rising': '상승', 'declining': '하락', 'stable': '안정'}[direction]

        return (f"{topic}이(가) {source_str} 등 {len(items)}개 소스에서 집중 조명. "
                f"트렌드 방향: {direction_kr}세. "
                f"최근 {len(items)}건의 관련 논의 확인.")

    def _synthesize_debate(self, topic: str, sentiments: Dict) -> str:
        """논쟁 종합"""
        pro_count = len(sentiments['positive'])
        con_count = len(sentiments['negative'])

        return (f"{topic}에 대해 찬성 {pro_count}건, 반대 {con_count}건의 의견 대립. "
                f"주요 쟁점은 실용성 vs 한계점.")

    def _generate_trend_actions(self, topic: str, direction: str) -> List[str]:
        """트렌드 기반 액션 아이템 생성"""
        actions = []

        if direction == 'rising':
            actions.append(f"{topic} 관련 기술 스택 학습 시작")
            actions.append(f"{topic} 커뮤니티/포럼 참여")
        elif direction == 'declining':
            actions.append(f"{topic} 대체 기술 조사")
            actions.append(f"기존 {topic} 의존도 감소 계획")

        actions.append(f"{topic} 관련 프로젝트 PoC 검토")

        return actions

    def _find_problems(self, items: List[Dict]) -> List[Dict]:
        """문제 언급 찾기"""
        problems = []
        problem_keywords = ['problem', 'issue', 'challenge', 'limitation', 'bottleneck']

        for item in items:
            content = self._get_content(item).lower()
            for keyword in problem_keywords:
                if keyword in content:
                    topics = self._extract_topics(item)
                    if topics:
                        problems.append({
                            'topic': topics[0],
                            'items': [item]
                        })
                    break

        return problems

    def _find_solutions(self, items: List[Dict]) -> List[Dict]:
        """해결책 언급 찾기"""
        solutions = []
        solution_keywords = ['solution', 'solve', 'fix', 'address', 'overcome']

        for item in items:
            content = self._get_content(item).lower()
            for keyword in solution_keywords:
                if keyword in content:
                    topics = self._extract_topics(item)
                    if topics:
                        solutions.append({
                            'topic': topics[0],
                            'items': [item]
                        })
                    break

        return solutions

    def _find_unmet_needs(self, problems: List[Dict], solutions: List[Dict]) -> List[Dict]:
        """미해결 문제 찾기"""
        solution_topics = set([s['topic'] for s in solutions])
        unmet = [p for p in problems if p['topic'] not in solution_topics]
        return unmet

    def _find_new_technologies(self, items: List[Dict]) -> List[Dict]:
        """새로운 기술 찾기"""
        new_tech = []
        new_keywords = ['announced', 'released', 'launched', 'introduced', 'unveiled']

        for item in items:
            content = self._get_content(item).lower()
            for keyword in new_keywords:
                if keyword in content:
                    topics = self._extract_topics(item)
                    if topics:
                        new_tech.append({
                            'name': topics[0],
                            'items': [item]
                        })
                    break

        return new_tech

    def _suggest_applications(self, tech: Dict) -> List[str]:
        """기술의 적용 분야 제안"""
        tech_name = tech['name'].lower()

        applications_map = {
            'llm': ['고객 서비스 자동화', '코드 리뷰 자동화', '문서 요약'],
            'rag': ['기업 내부 지식 검색', 'FAQ 시스템', '맞춤형 추천'],
            'agent': ['워크플로우 자동화', '리서치 자동화', '테스트 자동화'],
            'multimodal': ['콘텐츠 생성', '접근성 개선', '교육 자료 제작']
        }

        for key, apps in applications_map.items():
            if key in tech_name:
                return apps

        return ['프로토타입 제작', 'PoC 개발']

    def _analyze_evolution(self, timeline: List[Tuple[datetime, Dict]]) -> Optional[str]:
        """시간적 진화 패턴 분석"""
        if len(timeline) < 3:
            return None

        # 버전 진화 (v1 → v2 → v3)
        versions = []
        for _, item in timeline:
            title = item.get('title', '').lower()
            import re
            version_match = re.search(r'v?(\d+)\.(\d+)', title)
            if version_match:
                versions.append(version_match.group(0))

        if len(versions) >= 2:
            return f"버전 진화: {' → '.join(versions)}"

        # 성능 개선 패턴
        performance_keywords = ['faster', 'improved', 'better', 'enhanced']
        improvements = []
        for _, item in timeline:
            content = self._get_content(item).lower()
            for keyword in performance_keywords:
                if keyword in content:
                    improvements.append(item.get('title', '')[:30])
                    break

        if len(improvements) >= 2:
            return f"지속적 성능 개선: {len(improvements)}단계 진화"

        return None

    def _format_timeline(self, timeline: List[Tuple[datetime, Dict]]) -> str:
        """타임라인 포맷팅"""
        if not timeline:
            return ""

        dates = [date.strftime('%Y-%m-%d') for date, _ in timeline[:3]]
        return f"{dates[0]} → {dates[-1]}"

    def _get_timeline(self, items: List[Dict]) -> str:
        """아이템들의 시간 범위"""
        dates = [item.get('published_at', datetime.min) for item in items if 'published_at' in item]
        if not dates:
            return ""

        min_date = min(dates)
        max_date = max(dates)

        if min_date == max_date:
            return min_date.strftime('%Y-%m-%d')
        return f"{min_date.strftime('%Y-%m-%d')} ~ {max_date.strftime('%Y-%m-%d')}"


# 사용 예시
if __name__ == "__main__":
    # 샘플 데이터
    sample_items = [
        {
            'title': 'OpenAI announces GPT-4 Turbo with improved reasoning',
            'content': 'Major breakthrough in LLM performance...',
            'source': 'OpenAI Blog',
            'published_at': datetime(2024, 11, 1)
        },
        {
            'title': 'Claude 3.5 shows superior coding abilities',
            'content': 'Anthropic\'s latest model excels at programming...',
            'source': 'Anthropic Blog',
            'published_at': datetime(2024, 11, 2)
        },
        {
            'title': 'The problem with current LLM evaluation methods',
            'content': 'Critical analysis of benchmark limitations...',
            'source': 'Research Paper',
            'published_at': datetime(2024, 11, 3)
        }
    ]

    engine = InsightConnectionEngine()
    connected_insights = engine.find_connections(sample_items)

    print(f"발견된 연결 인사이트: {len(connected_insights)}개\n")

    for insight in connected_insights:
        print(f"{insight.title}")
        print(f"유형: {insight.insight_type}")
        print(f"연결 이유: {insight.connection_reason}")
        print(f"종합: {insight.synthesis}")
        print(f"신뢰도: {insight.confidence:.1%}")
        if insight.action_items:
            print(f"액션: {', '.join(insight.action_items)}")
        print("-" * 50)