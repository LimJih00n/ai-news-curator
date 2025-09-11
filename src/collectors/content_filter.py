from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import openai
import re


@dataclass
class ContentScore:
    title: str
    source: str
    relevance_score: float  # 0-10, AI/IT 관련성
    importance_score: float  # 0-10, 중요도
    combined_score: float    # 가중 평균
    reason: str             # 점수 근거


def simple_keyword_filter(items: List, max_items: int = 50) -> List:
    """기술 트렌드 & 혁신 중심의 스마트 필터링 (토큰 0개)"""
    from datetime import datetime, timedelta
    
    # 🚀 핵심 기술 트렌드 키워드 (최고 점수)
    tech_trend_keywords = [
        'GPT-5', 'GPT-6', 'Claude', 'Gemini', 'LLM', 'transformer', 'neural network',
        'AGI', 'artificial general intelligence', 'superintelligence',
        'multimodal', 'vision-language', 'audio-video generation',
        'robotics', 'autonomous', 'self-driving', 'drone', 'humanoid',
        'biotech', 'synthetic biology', 'gene editing', 'CRISPR',
        'space tech', 'satellite', 'rocket', 'mars', 'spacex',
        'web3', 'blockchain', 'cryptocurrency', 'NFT', 'DeFi',
        'metaverse', 'VR', 'AR', 'XR', 'mixed reality',
        'edge computing', '5G', '6G', 'IoT', 'smart city'
    ]
    
    # 🔬 연구 & 혁신 키워드 (높은 점수)
    research_innovation_keywords = [
        'research', 'study', 'paper', 'breakthrough', 'innovation', 'discovery',
        'new model', 'latest', 'announcement', 'release', 'update', 'version',
        'benchmark', 'performance', 'accuracy', 'efficiency', 'speed',
        'state-of-the-art', 'SOTA', 'cutting-edge', 'revolutionary',
        'novel', 'unprecedented', 'first time', 'milestone',
        '연구', '논문', '혁신', '발표', '출시', '업데이트', '최신',
        '벤치마크', '성능', '정확도', '효율성', '속도'
    ]
    
    # 🚀 스타트업 & 혁신 키워드 (높은 점수)
    startup_innovation_keywords = [
        'startup', 'unicorn', 'scaleup', 'venture', 'funding', 'series A', 'series B',
        'product launch', 'beta', 'alpha', 'pilot', 'trial', 'demo',
        'new company', 'emerging', 'disruptive', 'game-changing',
        'revolutionary', 'breakthrough', 'innovative', 'cutting-edge',
        '스타트업', '유니콘', '스케일업', '벤처', '투자', '시리즈A', '시리즈B',
        '제품 출시', '베타', '알파', '파일럿', '시연', '새로운 기업'
    ]
    
    # 🎯 구체적인 기술 제품/서비스 (높은 점수)
    specific_tech_products = [
        'Cursor', 'Cursor CLI', 'Cursor AI', 'Cursor editor',
        'GitHub Copilot', 'Copilot', 'Copilot X', 'Copilot Chat',
        'ChatGPT', 'ChatGPT Plus', 'ChatGPT Enterprise',
        'Midjourney', 'DALL-E', 'Stable Diffusion', 'Runway',
        'Notion AI', 'Notion', 'Airtable', 'Figma',
        'Slack', 'Discord', 'Zoom', 'Teams',
        'Tesla', 'SpaceX', 'Neuralink', 'Boring Company',
        'OpenAI', 'Anthropic', 'Google AI', 'Meta AI', 'Microsoft AI'
    ]
    
    # 🌟 프리미엄 YouTube 채널 (최고 점수 - 선별된 고품질 컨텐츠)
    premium_youtube_channels = [
        'chester_roh',           # Chester Roh - AI/개발 트렌드
        'sudoremove',            # Sudo Remove - 기술 인사이트
        'aiDotEngineer',         # AI Dot Engineer - AI 엔지니어링
        'TwoMinutePapers',       # Two Minute Papers - AI 논문 리뷰
        'Fireship',              # Fireship - 개발 트렌드
        'AIExplained-official'   # AI Explained - AI 심층 분석
    ]
    
    # ❌ 제외할 키워드 (비즈니스/정치 뉴스)
    exclude_keywords = [
        # 소송/법적 분쟁
        'lawsuit', 'sue', 'sued', 'legal', 'court', 'judge', 'ruling',
        'settlement', 'settled', 'dispute', 'conflict', 'battle',
        'antitrust', 'monopoly', 'regulation', 'regulatory',
        '소송', '고소', '법적', '법원', '판사', '판결', '합의', '분쟁',
        
        # 라이선스/계약
        'license', 'licensing', 'agreement', 'contract', 'deal',
        'partnership', 'acquisition', 'merger', 'buyout',
        'royalty', 'fee', 'payment', 'revenue', 'profit',
        '라이선스', '계약', '파트너십', '인수', '합병', '로열티',
        
        # 투자/재무
        'investment', 'funding', 'IPO', 'valuation', 'market cap',
        'earnings', 'revenue', 'profit', 'loss', 'quarterly',
        'stock', 'share', 'dividend', 'bankruptcy',
        '투자', '자금', '상장', '가치', '시가총액', '수익', '손실',
        
        # 정치/정책
        'government', 'policy', 'regulation', 'law', 'bill',
        'congress', 'senate', 'house', 'president', 'minister',
        '정부', '정책', '규제', '법안', '의회', '대통령', '장관',
        
        # 기타 비기술적 내용
        'poker', 'todo app', 'txt file', 'dial-up', 'AOL', 'font',
        'pokemon', 'freebsd', 'openssh', 'apple-1', 'windows xp',
        '포커', '할일', '다이얼업', '폰트', '포켓몬'
    ]
    
    # 🔴 지역/정치 뉴스 키워드 (낮은 점수)
    local_news_keywords = [
        '지자체', '시청', '도청', '구청', '지역', '지방', '정치', '행정',
        '투자 유치', '시리즈A', '시리즈B', '벤처', '창업', '한국', '국내'
    ]
    
    scored_items = []
    for item in items:
        title_lower = item.title.lower()
        content_lower = (item.content or "").lower()
        
        # 제외 키워드 체크 (즉시 제외)
        should_exclude = any(keyword.lower() in title_lower for keyword in exclude_keywords)
        if should_exclude:
            continue
        
        score = 0
        
        # 1. 핵심 기술 트렌드 (최고 점수)
        for keyword in tech_trend_keywords:
            if keyword.lower() in title_lower:
                score += 10  # 제목에 있으면 최고 점수
            elif keyword.lower() in content_lower:
                score += 5   # 내용에 있으면 높은 점수
        
        # 2. 연구 & 혁신 (높은 점수)
        for keyword in research_innovation_keywords:
            if keyword.lower() in title_lower:
                score += 8
            elif keyword.lower() in content_lower:
                score += 4
        
        # 3. 스타트업 & 혁신 (높은 점수)
        for keyword in startup_innovation_keywords:
            if keyword.lower() in title_lower:
                score += 8
            elif keyword.lower() in content_lower:
                score += 4
        
        # 4. 구체적인 기술 제품/서비스 (높은 점수)
        for keyword in specific_tech_products:
            if keyword.lower() in title_lower:
                score += 9
            elif keyword.lower() in content_lower:
                score += 5
        
        # 5. 지역/정치 뉴스는 점수 감점
        for keyword in local_news_keywords:
            if keyword.lower() in title_lower:
                score -= 5  # 지역 뉴스는 큰 점수 감점
            elif keyword.lower() in content_lower:
                score -= 2
        
        # 6. 출처별 가중치 (기술 중심)
        source_lower = item.source.lower()
        
        # YouTube 프리미엄 채널은 최고 가중치
        if source_lower == 'youtube':
            # 채널명 확인
            channel_name = getattr(item, 'channel', '')
            if channel_name:
                # 프리미엄 채널 확인
                for premium_channel in premium_youtube_channels:
                    if premium_channel.lower() in channel_name.lower():
                        score += 15  # 프리미엄 YouTube 채널은 최고 점수
                        break
                else:
                    score += 8  # 일반 YouTube 채널
        elif 'arxiv.org' in source_lower:
            score += 6  # 논문은 매우 높은 점수
        elif 'ai.googleblog.com' in source_lower:
            score += 5  # Google AI 블로그는 높은 점수
        elif 'openai.com' in source_lower:
            score += 5  # OpenAI는 높은 점수
        elif 'anthropic.com' in source_lower:
            score += 5  # Anthropic은 높은 점수
        elif 'news.ycombinator.com' in source_lower:
            score += 4  # Hacker News는 높은 점수
        elif 'techcrunch.com' in source_lower:
            score += 4  # TechCrunch는 높은 점수
        elif 'theverge.com' in source_lower:
            score += 4  # The Verge는 높은 점수
        elif 'wired.com' in source_lower:
            score += 4  # Wired는 높은 점수
        elif 'aitimes.com' in source_lower:
            score += 1  # AI Times는 기본 점수 (지역 뉴스 많음)
        
        # 7. 제목 길이 가중치 (구체적인 기술 내용일수록 긴 제목)
        if len(item.title) > 60:
            score += 2  # 더 긴 제목은 더 높은 점수
        elif len(item.title) > 40:
            score += 1
        
        # 8. 날짜 기반 가중치 (최신 콘텐츠 우선)
        try:
            # published_at이 있는 경우
            if hasattr(item, 'published_at') and item.published_at:
                from datetime import datetime, timedelta
                import pytz
                
                # 날짜 처리
                published_date = item.published_at
                if hasattr(published_date, 'tzinfo') and published_date.tzinfo is None:
                    # timezone 없으면 UTC로 가정
                    published_date = pytz.UTC.localize(published_date)
                
                now = datetime.now(pytz.UTC)
                days_old = (now - published_date).days
                
                # 날짜별 가중치
                if days_old <= 1:
                    score += 10  # 1일 이내: 최고 가중치
                elif days_old <= 3:
                    score += 7   # 3일 이내: 높은 가중치
                elif days_old <= 7:
                    score += 4   # 1주일 이내: 중간 가중치
                elif days_old <= 30:
                    score += 1   # 1달 이내: 낮은 가중치
                elif days_old > 365:
                    score -= 10  # 1년 이상: 큰 감점
                elif days_old > 90:
                    score -= 5   # 3달 이상: 감점
        except Exception as e:
            # 날짜 파싱 실패 시 무시
            pass
        
        # 9. 최소 점수 보장
        score = max(score, 1)
        
        scored_items.append((item, score))
    
    # 점수 순으로 정렬하고 상위 항목 반환
    scored_items.sort(key=lambda x: x[1], reverse=True)
    
    print(f"🚀 기술 트렌드 중심 필터링 완료: 상위 {max_items}개 항목")
    for i, (item, score) in enumerate(scored_items[:max_items]):
        print(f"{i+1}. {item.title[:70]}... (점수: {score})")
    
    return [item for item, score in scored_items[:max_items]]


def cheap_ai_filter_with_importance(
    openai_api_key: str, 
    items: List, 
    max_items: int = 20
) -> List[ContentScore]:
    """
    저렴한 모델(gpt-3.5-turbo)로 빠르게 필터링 + 중요도 평가 (1-5점)
    """
    client = openai.OpenAI(api_key=openai_api_key)
    scored_items = []
    
    print(f"AI 필터링 + 중요도 평가 시작: {len(items)}개 항목 중 {max_items}개 선별...")
    
    # 배치 처리로 효율성 향상
    batch_size = 5
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        batch_prompt = "다음 뉴스들을 평가해주세요. 각 뉴스에 대해 신선도, 임팩트, 혁신성을 종합 평가하세요:\n\n"
        
        for j, item in enumerate(batch):
            title_preview = item.title[:100]
            source = getattr(item, 'source', 'Unknown')
            batch_prompt += f"{j+1}. [{source}] {title_preview}\n"
        
        batch_prompt += """
평가 기준:
[신선도 - Freshness]
- 최신 발표/출시 (오늘-3일): +3점
- 트렌딩 이슈 (HN 상위, 화제): +2점
- 일반 뉴스 (1주일 이내): +1점

[임팩트 - Impact]
- 게임체인저 (GPT-5, Claude 3.5, 새 모델): +4점
- 주요 제품 출시 (Cursor, GitHub Copilot 업데이트): +3점
- 연구 돌파구 (SOTA 달성, 새로운 방법론): +2점
- 일반 업데이트: +1점

[혁신성 - Innovation]
- 완전히 새로운 접근: +3점
- 기존 기술 개선: +2점
- 점진적 발전: +1점

최종 점수 = (신선도 + 임팩트 + 혁신성) / 2
중요도 = 1~5 (최종 점수 기반)

응답 형식: 
1:최종점수,중요도 2:최종점수,중요도 3:최종점수,중요도 4:최종점수,중요도 5:최종점수,중요도

예시: 1:9,5 2:7,4 3:5,3 4:3,2 5:8,4"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # 저렴한 모델 사용
                messages=[{"role": "user", "content": batch_prompt}],
                temperature=0.1,
                max_tokens=150,
            )
            
            result = response.choices[0].message.content.strip()
            
            # 배치 결과 파싱
            parsed_scores = []
            parts = result.split()
            for part in parts:
                if ':' in part:
                    try:
                        score_part = part.split(':')[1]
                        if ',' in score_part:
                            rel_score, imp_score = score_part.split(',')
                            parsed_scores.append((float(rel_score), float(imp_score)))
                        else:
                            # 단일 점수인 경우 관련성으로 사용하고 중요도는 기본값
                            rel_score = float(score_part)
                            parsed_scores.append((rel_score, 3.0))
                    except:
                        parsed_scores.append((5.0, 3.0))  # 기본값
            
            # 부족한 점수는 기본값으로 채우기
            while len(parsed_scores) < len(batch):
                parsed_scores.append((5.0, 3.0))
            
            # 각 항목에 점수 부여
            for j, (item, (rel_score, imp_score)) in enumerate(zip(batch, parsed_scores)):
                # 가중 평균: 관련성 70%, 중요도 30%
                combined_score = (rel_score * 0.7) + (imp_score * 0.3)
                
                scored_items.append(ContentScore(
                    title=item.title,
                    source=item.source,
                    relevance_score=rel_score,
                    importance_score=imp_score,
                    combined_score=combined_score,
                    reason=f"관련성 {rel_score}점, 중요도 {imp_score}점"
                ))
                    
        except Exception as e:
            print(f"배치 평가 실패: {e}")
            # 실패한 배치는 기본 점수 부여
            for item in batch:
                scored_items.append(ContentScore(
                    title=item.title,
                    source=item.source,
                    relevance_score=5.0,
                    importance_score=3.0,
                    combined_score=4.4,
                    reason="배치 평가 실패로 기본 점수"
                ))
    
    # 점수 순으로 정렬하고 상위 항목만 반환
    scored_items.sort(key=lambda x: x.combined_score, reverse=True)
    
    print(f"AI 필터링 + 중요도 평가 완료: 상위 {max_items}개 항목 선별됨")
    for i, item in enumerate(scored_items[:max_items]):
        stars = "⭐" * int(item.importance_score)
        print(f"{i+1}. {stars} {item.title[:50]}... (종합: {item.combined_score:.1f})")
    
    return scored_items[:max_items]

def cheap_ai_filter(
    openai_api_key: str, 
    items: List, 
    max_items: int = 20
) -> List[ContentScore]:
    """
    기존 저렴한 모델 필터링 (하위 호환성)
    """
    return cheap_ai_filter_with_importance(openai_api_key, items, max_items)


def get_filtered_items(openai_api_key: str, items: List, max_items: int = 20) -> List:
    """
    하이브리드 필터링: 키워드 → AI 중요도 평가 → 최종 선별
    """
    print(f"하이브리드 필터링 시작: {len(items)}개 항목")
    
    # 1단계: 키워드로 50개로 줄이기 (토큰 0개)
    keyword_filtered = simple_keyword_filter(items, 50)
    print(f"1단계 키워드 필터링 완료: {len(keyword_filtered)}개")
    
    # 2단계: 저렴한 AI로 중요도 평가하여 선별
    ai_scored = cheap_ai_filter_with_importance(openai_api_key, keyword_filtered, max_items)
    
    # 3단계: 선별된 항목들의 원본 데이터에 중요도 점수 첨부
    filtered_items = []
    scored_dict = {item.title: item for item in ai_scored}
    
    for item in keyword_filtered:
        if item.title in scored_dict:
            scored_item = scored_dict[item.title]
            # 원본 아이템에 중요도 점수 추가
            item.importance_score = scored_item.importance_score
            item.relevance_score = scored_item.relevance_score
            item.combined_score = scored_item.combined_score
            item.score_reason = scored_item.reason
            filtered_items.append(item)
            if len(filtered_items) >= max_items:
                break
    
    # 중요도 순으로 정렬 (높은 중요도 우선)
    filtered_items.sort(key=lambda x: getattr(x, 'importance_score', 3.0), reverse=True)
    
    print(f"최종 선별 완료: 중요도 기준 상위 {len(filtered_items)}개")
    
    return filtered_items
