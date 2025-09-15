"""
논문 전용 수집 및 평가 시스템
arXiv, Papers with Code 등 학술 논문 특화 처리
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import arxiv
import openai
from src.models import ArxivItem


@dataclass
class PaperScore:
    """논문 평가 점수"""
    title: str
    novelty_score: float      # 0-10, 참신성
    impact_score: float       # 0-10, 영향력
    practical_score: float    # 0-10, 실용성
    clarity_score: float      # 0-10, 명료성
    overall_score: float      # 종합 점수
    reason: str              # 평가 근거
    recommendation: str      # 추천 이유


class EnhancedPaperCollector:
    """개선된 논문 수집기"""
    
    # 중요 카테고리 우선순위
    PRIORITY_CATEGORIES = {
        'cs.AI': 10,      # Artificial Intelligence
        'cs.LG': 9,       # Machine Learning
        'cs.CL': 8,       # Computation and Language (NLP)
        'cs.CV': 8,       # Computer Vision
        'cs.NE': 7,       # Neural and Evolutionary Computing
        'cs.RO': 6,       # Robotics
        'stat.ML': 7,     # Machine Learning (Statistics)
        'cs.DC': 5,       # Distributed Computing
        'cs.CR': 5,       # Cryptography and Security
    }
    
    # 핫 키워드 (AI/RAG/Agent 트렌드 중심)
    HOT_KEYWORDS = [
        # 🤖 AI Agent 핵심 (최우선)
        'agent', 'multi-agent', 'autonomous agent', 'ai agent', 'intelligent agent',
        'agentic', 'agent-based', 'swarm intelligence', 'agent collaboration',
        'tool use', 'tool calling', 'function calling', 'tool learning',
        'planning', 'reasoning', 'decision making', 'action selection',
        
        # 🔍 RAG 시스템 (최우선)
        'rag', 'retrieval augmented', 'retrieval-augmented generation',
        'vector database', 'embedding', 'semantic search', 'vector search',
        'knowledge retrieval', 'document retrieval', 'context retrieval',
        'hybrid search', 'dense retrieval', 'sparse retrieval',
        'chunk', 'chunking', 'knowledge base', 'external knowledge',
        
        # 🧠 LLM 핵심 기술
        'llm', 'large language model', 'gpt', 'claude', 'gemini',
        'transformer', 'attention', 'self-attention', 'cross-attention',
        'foundation model', 'pretrained model', 'fine-tuning',
        'rlhf', 'reinforcement learning from human feedback',
        'constitutional ai', 'alignment', 'safety',
        
        # 💭 추론 및 사고
        'chain of thought', 'cot', 'step-by-step reasoning',
        'in-context learning', 'few-shot', 'zero-shot', 'one-shot',
        'prompt engineering', 'prompt optimization', 'instruction tuning',
        'tree of thoughts', 'self-consistency', 'reflection',
        
        # 🔧 효율성 기술
        'lora', 'qlora', 'adapter', 'parameter efficient',
        'quantization', 'pruning', 'distillation', 'compression',
        'inference optimization', 'model compression',
        
        # 🌐 멀티모달
        'multimodal', 'vision-language', 'vlm', 'image-text',
        'video understanding', 'audio-visual', 'cross-modal',
        
        # 📊 평가 및 벤치마크
        'benchmark', 'evaluation', 'sota', 'state-of-the-art',
        'outperform', 'surpass', 'achieve', 'leaderboard',
        'human evaluation', 'automatic evaluation'
    ]
    
    def __init__(self):
        self.search_client = arxiv.Client()
    
    def fetch_papers(self, 
                    query: str = None,
                    categories: List[str] = None,
                    max_results: int = 30,
                    days_back: int = 7) -> List[ArxivItem]:
        """
        논문 수집 (카테고리별 + 키워드 검색)
        
        Args:
            query: 검색 쿼리 (None이면 카테고리만)
            categories: 카테고리 리스트
            max_results: 최대 결과 수
            days_back: 며칠 전까지 검색
        """
        all_papers = []
        
        # 기본 카테고리 설정
        if not categories:
            categories = list(self.PRIORITY_CATEGORIES.keys())
        
        # 카테고리별 검색
        for category in categories:
            cat_query = f"cat:{category}"
            if query:
                cat_query = f"({cat_query}) AND ({query})"
            
            papers = self._search_arxiv(cat_query, max_results=10)
            all_papers.extend(papers)
        
        # 중복 제거 (ID 기반)
        seen_ids = set()
        unique_papers = []
        for paper in all_papers:
            if paper.link not in seen_ids:
                seen_ids.add(paper.link)
                unique_papers.append(paper)
        
        # 날짜 필터링
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_papers = [p for p in unique_papers 
                        if p.published_at and p.published_at.replace(tzinfo=None) > cutoff_date]
        
        # 우선순위 정렬
        sorted_papers = self._prioritize_papers(recent_papers)
        
        print(f"[PAPERS] 논문 수집 완료: {len(sorted_papers)}개 (최근 {days_back}일)")
        return sorted_papers[:max_results]
    
    def _search_arxiv(self, query: str, max_results: int = 10) -> List[ArxivItem]:
        """arXiv 검색 실행"""
        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            papers = []
            for result in search.results():
                try:
                    papers.append(
                        ArxivItem(
                            source="arXiv",
                            title=result.title.replace('\n', ' ').strip(),
                            link=result.entry_id,
                            published_at=result.published,
                            abstract=result.summary.replace('\n', ' ').strip(),
                            authors=[author.name for author in result.authors],
                            categories=result.categories if hasattr(result, 'categories') else [],
                        )
                    )
                except Exception as e:
                    print(f"논문 파싱 실패: {e}")
                    continue
            
            return papers
            
        except Exception as e:
            print(f"arXiv 검색 실패: {e}")
            return []
    
    def _prioritize_papers(self, papers: List[ArxivItem]) -> List[ArxivItem]:
        """논문 우선순위 정렬"""
        def calculate_priority(paper: ArxivItem) -> float:
            score = 0
            
            # 카테고리 점수
            for category in paper.categories:
                score += self.PRIORITY_CATEGORIES.get(category, 3)
            
            # 핫 키워드 점수
            title_lower = paper.title.lower()
            abstract_lower = paper.abstract.lower() if paper.abstract else ""
            
            for keyword in self.HOT_KEYWORDS:
                if keyword in title_lower:
                    score += 5
                elif keyword in abstract_lower:
                    score += 2
            
            # 최신성 점수
            if paper.published_at:
                days_old = (datetime.now() - paper.published_at.replace(tzinfo=None)).days
                if days_old <= 1:
                    score += 10
                elif days_old <= 3:
                    score += 7
                elif days_old <= 7:
                    score += 4
            
            # 저자 수 (협업 규모)
            if len(paper.authors) > 5:
                score += 3  # 대규모 협업
            
            return score
        
        papers.sort(key=calculate_priority, reverse=True)
        return papers


class PaperEvaluator:
    """논문 전용 평가 시스템"""
    
    def __init__(self, openai_api_key: str):
        self.client = openai.OpenAI(api_key=openai_api_key)
    
    def evaluate_papers(self, papers: List[ArxivItem], max_papers: int = 10) -> List[Tuple[ArxivItem, PaperScore]]:
        """
        논문 평가 (논문 특화 기준)
        """
        evaluated_papers = []
        
        print(f"[EVAL] 논문 평가 시작: {len(papers)}개 중 상위 {max_papers}개 선별...")
        
        # 배치 처리
        batch_size = 3
        for i in range(0, min(len(papers), max_papers * 2), batch_size):
            batch = papers[i:i+batch_size]
            batch_scores = self._evaluate_batch(batch)
            
            for paper, score in zip(batch, batch_scores):
                evaluated_papers.append((paper, score))
        
        # 점수 순 정렬
        evaluated_papers.sort(key=lambda x: x[1].overall_score, reverse=True)
        
        # 상위 논문 출력
        print(f"\n📊 상위 {max_papers}개 논문:")
        for i, (paper, score) in enumerate(evaluated_papers[:max_papers], 1):
            print(f"{i}. [{score.overall_score:.1f}점] {paper.title[:60]}...")
            print(f"   └ {score.recommendation}")
        
        return evaluated_papers[:max_papers]
    
    def _evaluate_batch(self, papers: List[ArxivItem]) -> List[PaperScore]:
        """배치 평가"""
        prompt = "다음 AI/ML 논문들을 평가해주세요:\n\n"
        
        for i, paper in enumerate(papers, 1):
            prompt += f"{i}. 제목: {paper.title[:100]}\n"
            prompt += f"   카테고리: {', '.join(paper.categories[:3])}\n"
            prompt += f"   초록: {paper.abstract[:200]}...\n\n"
        
        prompt += """
🤖 AI/RAG/Agent 트렌드 중심으로 각 논문을 평가하세요:

[AI Agent 혁신성] (0-10) - 가중치 30%
- 자율적 추론/계획/실행 혁신: 9-10점
- Multi-agent 협업 시스템: 8-9점
- Tool use/Function calling 개선: 7-8점
- 기존 Agent 아키텍처 개선: 5-6점

[RAG 시스템 기여도] (0-10) - 가중치 30%
- 검색 정확도 획기적 개선: 9-10점
- Vector DB/Embedding 혁신: 8-9점
- 하이브리드 검색 기법: 7-8점
- 기존 RAG 성능 개선: 5-6점

[LLM 핵심 기술] (0-10) - 가중치 25%
- 추론 능력 혁신(CoT, ToT): 9-10점
- 효율성 혁신(LoRA, 양자화): 8-9점
- Alignment/Safety 기여: 7-8점
- 일반적 성능 개선: 5-6점

[실무 적용성] (0-10) - 가중치 15%
- 즉시 프로덕션 적용: 9-10점
- 3개월 내 적용 가능: 7-8점
- 6개월 내 적용 가능: 5-6점
- 연구용/이론적: 3-4점

⭐ 우선 관심 키워드 보너스 (+2점):
Agent, RAG, Tool Use, Multi-modal, Chain-of-Thought, Retrieval

응답 형식:
1:Agent혁신,RAG기여,LLM기술,실무적용|핵심기여요약
2:Agent혁신,RAG기여,LLM기술,실무적용|핵심기여요약

예시:
1:9,8,7,9|자율 코딩 Agent의 도구 사용 능력 획기적 개선
2:6,9,6,8|RAG 검색 정확도를 30% 향상시키는 새로운 임베딩 기법"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            result = response.choices[0].message.content.strip()
            return self._parse_evaluation(result, papers)
            
        except Exception as e:
            print(f"평가 실패: {e}")
            # 기본 점수 반환
            return [self._default_score(paper) for paper in papers]
    
    def _parse_evaluation(self, result: str, papers: List[ArxivItem]) -> List[PaperScore]:
        """평가 결과 파싱"""
        scores = []
        lines = result.strip().split('\n')
        
        for i, paper in enumerate(papers):
            try:
                if i < len(lines):
                    parts = lines[i].split('|')
                    score_part = parts[0].split(':')[1] if ':' in parts[0] else parts[0]
                    score_values = [float(x) for x in score_part.split(',')]
                    
                    while len(score_values) < 4:
                        score_values.append(5.0)
                    
                    recommendation = parts[1] if len(parts) > 1 else "주목할 만한 연구"
                    
                    # 가중치 적용한 종합 점수 계산
                    weighted_score = (
                        score_values[0] * 0.30 +  # AI Agent 혁신성 30%
                        score_values[1] * 0.30 +  # RAG 시스템 기여도 30%  
                        score_values[2] * 0.25 +  # LLM 핵심 기술 25%
                        score_values[3] * 0.15    # 실무 적용성 15%
                    )
                    
                    scores.append(PaperScore(
                        title=paper.title,
                        novelty_score=score_values[0],  # Agent 혁신성
                        impact_score=score_values[1],   # RAG 기여도
                        practical_score=score_values[2], # LLM 기술
                        clarity_score=score_values[3],   # 실무 적용성
                        overall_score=weighted_score,
                        reason=f"Agent {score_values[0]}, RAG {score_values[1]}, LLM {score_values[2]}, 실용 {score_values[3]}",
                        recommendation=recommendation
                    ))
                else:
                    scores.append(self._default_score(paper))
                    
            except Exception as e:
                print(f"파싱 오류: {e}")
                scores.append(self._default_score(paper))
        
        return scores
    
    def _default_score(self, paper: ArxivItem) -> PaperScore:
        """기본 점수"""
        return PaperScore(
            title=paper.title,
            novelty_score=5.0,
            impact_score=5.0,
            practical_score=5.0,
            clarity_score=5.0,
            overall_score=5.0,
            reason="자동 평가",
            recommendation="검토 필요"
        )