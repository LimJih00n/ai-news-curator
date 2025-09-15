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
    
    # 핵심 기술 트렌드 키워드 (최고 점수) - 2024-2025 실무 중심
    tech_trend_keywords = [
        # AI 모델 & 서비스 (최신)
        'GPT-4o', 'GPT-5', 'Claude 3.5', 'Claude Opus', 'Gemini Pro', 'Gemini Ultra',
        'Llama 3', 'Mistral', 'Mixtral', 'Qwen', 'DeepSeek', 'Phi-3',
        'ChatGPT Canvas', 'ChatGPT Voice', 'ChatGPT Code Interpreter',
        'Anthropic Artifacts', 'Google Bard', 'Microsoft Copilot',

        # AI 개발 도구 (실무)
        'Cursor', 'Cursor AI', 'Windsurf', 'v0.dev', 'Vercel AI SDK',
        'GitHub Copilot', 'Copilot Workspace', 'Amazon CodeWhisperer',
        'LangChain', 'LlamaIndex', 'AutoGPT', 'CrewAI', 'Autogen',
        'RAG', 'vector database', 'embedding', 'fine-tuning', 'LoRA', 'QLoRA',
        'Pinecone', 'Weaviate', 'Chroma', 'Qdrant', 'pgvector',

        # AI Agent & Automation
        'AI agent', 'autonomous agent', 'multi-agent', 'agent framework',
        'function calling', 'tool use', 'ReAct', 'Chain of Thought',
        'Tree of Thoughts', 'Graph of Thoughts', 'prompt engineering',

        # 실용 AI 응용
        'Midjourney v6', 'DALL-E 3', 'Stable Diffusion XL', 'SDXL Turbo',
        'Flux', 'Leonardo AI', 'Runway Gen-3', 'Pika Labs', 'HeyGen',
        'ElevenLabs', 'Whisper', 'Suno AI', 'Udio', 'NotebookLM',

        # 최신 기술 트렌드
        'multimodal AI', 'vision-language model', 'video generation',
        'real-time AI', 'edge AI', 'on-device AI', 'WebGPU', 'WebAssembly',
        'serverless AI', 'AI inference optimization', 'quantization'
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
    
    # 프리미엄 YouTube 채널 (최고 점수 - 선별된 고품질 컨텐츠)
    premium_youtube_channels = [
        # 한국어 AI/개발 채널
        'chester_roh',           # Chester Roh - AI/개발 트렌드
        'sudoremove',            # Sudo Remove - 기술 인사이트
        'aiDotEngineer',         # AI Dot Engineer - AI 엔지니어링
        '노마드코더',               # 노마드코더 - 개발 교육
        '코딩애플',               # 코딩애플 - iOS/개발
        '드림코딩',               # 드림코딩 - 개발 교육
        '조코딩',                 # 조코딩 - AI/개발
        '테디노트',               # 테디노트 - AI 트렌드

        # 영어 AI/Tech 채널
        'TwoMinutePapers',       # Two Minute Papers - AI 논문 리뷰
        'Fireship',              # Fireship - 개발 트렌드
        'AIExplained-official',  # AI Explained - AI 심층 분석
        'YannicKilcher',         # Yannic Kilcher - AI 논문 리뷰
        'ThePrimeTime',          # ThePrimeTime - 개발 트렌드
        'ArjanCodes',            # ArjanCodes - Python/설계
        'mCoding',               # mCoding - Python 심화
        'NetworkChuck'           # NetworkChuck - DevOps/보안
    ]
    
    # 제외할 키워드 (비즈니스/정치 뉴스 + 구식 기술)
    exclude_keywords = [
        # 소송/법적 분쟁
        'lawsuit', 'sue', 'sued', 'legal', 'court', 'judge', 'ruling',
        'settlement', 'settled', 'dispute', 'conflict', 'battle',
        'antitrust', 'monopoly', 'regulation', 'regulatory', 'compliance',
        '소송', '고소', '법적', '법원', '판사', '판결', '합의', '분쟁', '규제',

        # 단순 투자/인수 소식
        'series A', 'series B', 'series C', 'seed funding', 'pre-seed',
        'raised', 'raises', 'funding round', 'valuation', 'unicorn status',
        '시리즈A', '시리즈B', '투자 유치', '유니콘 달성', '기업가치',

        # 정치/정책/지역 뉴스
        'government', 'policy', 'politics', 'election', 'vote',
        'congress', 'senate', 'house', 'president', 'minister',
        '정부', '정책', '선거', '투표', '의회', '대통령', '장관',
        '지자체', '시청', '도청', '구청', '지역', '지방',

        # 구식 기술/관련 없는 내용
        'poker', 'todo app', 'txt file', 'dial-up', 'AOL', 'font',
        'pokemon', 'freebsd', 'openssh', 'apple-1', 'windows xp',
        'windows 95', 'internet explorer', 'netscape', 'flash player',
        'jquery', 'backbone.js', 'grunt', 'gulp', 'bower',
        'PHP 5', 'Python 2', 'Angular 1', 'React class components',
        '포커', '할일', '다이얼업', '폰트', '포켓몬',

        # 단순 기업 소식
        'layoff', 'layoffs', 'fired', 'hiring freeze', 'restructuring',
        'earnings call', 'quarterly report', 'stock price', 'market share',
        '해고', '구조조정', '실적발표', '주가', '시장점유율'
    ]
    
    # 지역/비실용적 뉴스 키워드 (낮은 점수)
    low_priority_keywords = [
        # 지역 뉴스
        '지자체', '시청', '도청', '구청', '지역', '지방', '정치', '행정',
        '한국 정부', '국내 스타트업', 'K-', '한국형',

        # 단순 이벤트/컨퍼런스
        'conference', 'summit', 'meetup', 'webinar', 'workshop',
        '컨퍼런스', '행사', '박람회', '세미나', '워크샵',

        # 과대 평가된 일반 뉴스
        'opinion', 'editorial', 'interview', 'podcast', 'newsletter',
        'year in review', 'predictions', 'trends', 'outlook',
        '의견', '인터뷰', '팔케스트', '전망', '예측'
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
        
        # 5. 비실용적 뉴스는 점수 감점
        for keyword in low_priority_keywords:
            if keyword.lower() in title_lower:
                score -= 5  # 비실용적 뉴스는 큰 점수 감점
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
        
        # 8. 날짜 기반 가중치 (최신 콘텐츠 강력 우선 - 더 엄격하게)
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

                # 날짜별 가중치 (훨씬 더 엄격하게)
                if days_old <= 1:
                    score += 20  # 1일 이내: 최고 가중치 (2배 증가)
                elif days_old <= 2:
                    score += 15  # 2일 이내: 매우 높은 가중치
                elif days_old <= 3:
                    score += 10  # 3일 이내: 높은 가중치
                elif days_old <= 7:
                    score += 3   # 1주일 이내: 낮은 가중치
                elif days_old <= 14:
                    score -= 5   # 2주 이상: 감점 시작
                elif days_old <= 30:
                    score -= 10  # 1달 이상: 큰 감점
                elif days_old > 60:
                    score -= 30  # 2달 이상: 거의 제외
                else:
                    score -= 15  # 1-2달: 상당한 감점

                # 극도로 오래된 컨텐츠는 점수를 매우 낮게
                if days_old > 90:
                    score = -100  # 3달 이상 오래된 뉴스는 사실상 제외
        except Exception as e:
            # 날짜 파싱 실패 시 감점 (날짜가 없으면 오래된 것으로 간주)
            score -= 5

        # 점수가 음수면 제외
        if score <= 0:
            continue

        # 9. 최소 점수 보장
        score = max(score, 1)

        scored_items.append((item, score))
    
    # 점수 순으로 정렬하고 상위 항목 반환
    scored_items.sort(key=lambda x: x[1], reverse=True)
    
    print(f"[FILTER] 기술 트렌드 중심 필터링 완료: 상위 {max_items}개 항목")
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
[STRICT] 실무 개발자 관점으로 엄격하게 평가! (5점 만점, 평균 2-3점 유지)

[MUST EXCLUDE] 반드시 제외 (1점):
- 단순 투자/인수 소식 ("XX사가 YY억 투자 유치")
- 지역/국가 정책 뉴스 ("한국 정부가...", "EU 규제...")
- 과거 기술 회고 ("10년 전 이 기술이...")
- 비기술적 기업 뉴스 ("실적 발표", "주가 상승")
- 단순 ChatGPT 사용법 ("이렇게 하면 ChatGPT가...")
- 예측/전망 기사 ("2030년에는...", "AI의 미래는...")

[HIGH SCORE] 즉시 적용 가능한 실무 기술 (4-5점):
- 새 AI 모델 출시 (Claude 3.5 Sonnet, GPT-4o mini, Gemini 1.5 Flash)
- AI 코딩 도구 업데이트 (Cursor, Windsurf, v0.dev)
- RAG/Agent 프레임워크 (LangChain, CrewAI, AutoGen)
- 새로운 프롬프트 기법 (Chain-of-Thought, Few-shot)
- AI 성능 최적화 (LoRA, QLoRA, 양자화, 온디바이스)
- 실용 AI API/SDK (OpenAI, Anthropic, Vercel AI)

평가 기준:
1점: 관련 없음/매우 낮은 중요도
2점: 약간 관련/일반 업데이트  
3점: 관련 있음/중간 중요도
4점: 매우 관련/높은 중요도
5점: 혁신적/게임체인저

응답 형식: 1:점수 2:점수 3:점수 4:점수 5:점수
예시: 1:5 2:2 3:1 4:4 5:3

[CRITICAL] 5점은 정말 혁신적인 기술에만! 대부분 1-3점!"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # 저렴한 모델 사용
                messages=[{"role": "user", "content": batch_prompt}],
                temperature=0.1,
                max_tokens=150,
            )
            
            result = response.choices[0].message.content.strip()
            
            # 배치 결과 파싱 (새로운 형식)
            parsed_scores = []
            parts = result.split()
            for part in parts:
                if ':' in part:
                    try:
                        score_part = part.split(':')[1]
                        # 단일 점수 형식으로 변경 (1:5 2:2 3:1 형식)
                        score = float(score_part)
                        # 점수를 관련성과 중요도로 매핑 (점수가 곧 중요도)
                        parsed_scores.append((score, score))
                    except:
                        parsed_scores.append((2.0, 2.0))  # 기본값 낮춤
            
            # 부족한 점수는 기본값으로 채우기 (낮게)
            while len(parsed_scores) < len(batch):
                parsed_scores.append((2.0, 2.0))
            
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
            # 실패한 배치는 낮은 기본 점수 부여
            for item in batch:
                scored_items.append(ContentScore(
                    title=item.title,
                    source=item.source,
                    relevance_score=2.0,
                    importance_score=2.0,
                    combined_score=2.0,
                    reason="배치 평가 실패로 낮은 기본 점수"
                ))
    
    # 점수 순으로 정렬하고 상위 항목만 반환
    scored_items.sort(key=lambda x: x.combined_score, reverse=True)
    
    print(f"AI 필터링 + 중요도 평가 완료: 상위 {max_items}개 항목 선별됨")
    for i, item in enumerate(scored_items[:max_items]):
        stars = "*" * int(item.importance_score)
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
