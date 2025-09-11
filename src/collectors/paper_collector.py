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
    
    # 핫 키워드 (최신 트렌드)
    HOT_KEYWORDS = [
        # 모델 관련
        'llm', 'large language model', 'gpt', 'transformer', 'diffusion',
        'multimodal', 'vision-language', 'foundation model', 'agent',
        
        # 기법 관련
        'rlhf', 'reinforcement learning from human feedback',
        'chain of thought', 'in-context learning', 'prompt engineering',
        'lora', 'qlora', 'efficient', 'quantization', 'distillation',
        
        # 응용 관련
        'reasoning', 'code generation', 'retrieval augmented', 'rag',
        'tool use', 'function calling', 'alignment', 'safety',
        
        # 벤치마크
        'benchmark', 'evaluation', 'sota', 'state-of-the-art',
        'outperform', 'surpass', 'achieve'
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
        
        print(f"📚 논문 수집 완료: {len(sorted_papers)}개 (최근 {days_back}일)")
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
        
        print(f"🔬 논문 평가 시작: {len(papers)}개 중 상위 {max_papers}개 선별...")
        
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
각 논문을 다음 기준으로 평가하세요:

[참신성 - Novelty] (0-10)
- 완전히 새로운 접근/아이디어: 8-10점
- 기존 방법의 창의적 개선: 5-7점
- 점진적 개선: 3-4점

[영향력 - Impact] (0-10)
- 패러다임 전환 가능성: 8-10점
- 실질적 성능 개선: 5-7점
- 제한적 개선: 3-4점

[실용성 - Practicality] (0-10)
- 즉시 적용 가능: 8-10점
- 약간의 수정으로 적용: 5-7점
- 이론적 기여: 3-4점

[명료성 - Clarity] (0-10)
- 매우 명확한 설명: 8-10점
- 이해 가능한 수준: 5-7점
- 복잡하고 난해: 3-4점

응답 형식:
1:참신성,영향력,실용성,명료성|한줄추천
2:참신성,영향력,실용성,명료성|한줄추천
3:참신성,영향력,실용성,명료성|한줄추천

예시:
1:8,7,6,9|Transformer 이후 가장 혁신적인 아키텍처 제안
2:6,5,8,7|실무에 즉시 적용 가능한 효율적인 파인튜닝 기법"""
        
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
                    
                    scores.append(PaperScore(
                        title=paper.title,
                        novelty_score=score_values[0],
                        impact_score=score_values[1],
                        practical_score=score_values[2],
                        clarity_score=score_values[3],
                        overall_score=sum(score_values) / 4,
                        reason=f"참신성 {score_values[0]}, 영향력 {score_values[1]}",
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