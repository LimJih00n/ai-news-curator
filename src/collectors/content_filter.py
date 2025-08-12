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


def cheap_ai_filter(
    openai_api_key: str, 
    items: List, 
    max_items: int = 20
) -> List[ContentScore]:
    """
    저렴한 모델(gpt-3.5-turbo)로 빠르게 필터링
    """
    client = openai.OpenAI(api_key=openai_api_key)
    scored_items = []
    
    print(f"저렴한 AI 필터링 시작: {len(items)}개 항목 중 {max_items}개 선별...")
    
    # 배치 처리로 효율성 향상
    batch_size = 5
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        batch_prompt = "다음 기사들을 **기술 트렌드와 혁신** 관점에서 평가해주세요 (0-10점):\n\n"
        
        for j, item in enumerate(batch):
            title_preview = item.title[:100]
            batch_prompt += f"{j+1}. {title_preview}\n"
        
        batch_prompt += """
평가 기준:
- 🌟 **YouTube 프리미엄 컨텐츠** (Chester Roh, Fireship, Two Minute Papers 등): 9-10점
- 🚀 **최신 기술 트렌드** (GPT-5, Claude, AI 모델 등): 8-10점
- 🔬 **연구 혁신** (새로운 논문, 벤치마크, 성능 향상): 7-9점  
- 💡 **스타트업 혁신** (새로운 제품, 혁신적 서비스): 7-9점
- 🎯 **구체적인 기술 제품** (Cursor CLI, 새로운 AI 도구): 7-9점
- 📰 **일반 기술 뉴스**: 4-6점
- ❌ **소송/라이선스/투자 뉴스**: 0-3점

응답 형식: 1:점수, 2:점수, 3:점수, 4:점수, 5:점수"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # 저렴한 모델 사용
                messages=[{"role": "user", "content": batch_prompt}],
                temperature=0.1,
                max_tokens=100,
            )
            
            result = response.choices[0].message.content.strip()
            
            # 배치 결과 파싱
            scores = []
            for line in result.split(','):
                if ':' in line:
                    try:
                        score = float(line.split(':')[1].strip())
                        scores.append(score)
                    except:
                        scores.append(5.0)  # 기본값
                else:
                    scores.append(5.0)
            
            # 각 항목에 점수 부여
            for j, (item, score) in enumerate(zip(batch, scores)):
                if j < len(scores):
                    scored_items.append(ContentScore(
                        title=item.title,
                        source=item.source,
                        relevance_score=score,
                        importance_score=score,  # 간단하게 동일 점수
                        combined_score=score,
                        reason=f"배치 AI 평가: {score}점"
                    ))
                else:
                    scored_items.append(ContentScore(
                        title=item.title,
                        source=item.source,
                        relevance_score=5.0,
                        importance_score=5.0,
                        combined_score=5.0,
                        reason="기본 점수"
                    ))
                    
        except Exception as e:
            print(f"배치 평가 실패: {e}")
            # 실패한 배치는 기본 점수 부여
            for item in batch:
                scored_items.append(ContentScore(
                    title=item.title,
                    source=item.source,
                    relevance_score=5.0,
                    importance_score=5.0,
                    combined_score=5.0,
                    reason="배치 평가 실패로 기본 점수"
                ))
    
    # 점수 순으로 정렬하고 상위 항목만 반환
    scored_items.sort(key=lambda x: x.combined_score, reverse=True)
    
    print(f"AI 필터링 완료: 상위 {max_items}개 항목 선별됨")
    for i, item in enumerate(scored_items[:max_items]):
        print(f"{i+1}. {item.title[:60]}... (점수: {item.combined_score:.1f})")
    
    return scored_items[:max_items]


def get_filtered_items(openai_api_key: str, items: List, max_items: int = 20) -> List:
    """
    하이브리드 필터링: 키워드 → AI → 최종 선별
    """
    print(f"하이브리드 필터링 시작: {len(items)}개 항목")
    
    # 1단계: 키워드로 50개로 줄이기 (토큰 0개)
    keyword_filtered = simple_keyword_filter(items, 50)
    print(f"1단계 키워드 필터링 완료: {len(keyword_filtered)}개")
    
    # 2단계: 저렴한 AI로 20개 선별
    ai_filtered = cheap_ai_filter(openai_api_key, keyword_filtered, max_items)
    
    # 3단계: 선별된 항목들의 원본 데이터 반환
    filtered_items = []
    scored_titles = {item.title for item in ai_filtered}
    
    for item in keyword_filtered:
        if item.title in scored_titles:
            filtered_items.append(item)
            if len(filtered_items) >= max_items:
                break
    
    return filtered_items
