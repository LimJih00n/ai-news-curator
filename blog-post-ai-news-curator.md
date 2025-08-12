# 매일 아침 AI 뉴스를 자동 수집하는 시스템 개발기

## 시작 배경

매일 아침 해커뉴스, Reddit, arXiv를 돌면서 AI 소식을 확인하는 루틴이 있었다. 30분에서 1시간 정도 소요되는데, 이걸 자동화할 수 있지 않을까 생각했다.

목표는 단순했다:
- 50개 이상의 소스에서 뉴스를 자동 수집
- AI로 중요한 것만 선별 (상위 20개)
- 한국어로 요약해서 Notion과 텔레그램으로 전송
- GitHub Actions로 매일 자동 실행

2주간의 개발 과정과 주요 기술적 결정들을 정리한다.

## 기술 스택과 아키텍처 설계

### 기술 스택 선정

빠른 프로토타이핑을 위해 익숙한 도구들을 선택했다:
- **Python 3.11**: 데이터 처리에 최적화
- **OpenAI API**: GPT-3.5-turbo (필터링) + GPT-4o-mini (요약)
- **Notion API**: 결과 저장 및 소스 관리
- **Telegram Bot API**: 실시간 알림
- **GitHub Actions**: 무료 크론 서비스

### 시스템 아키텍처

모듈화된 구조로 설계했다:
```
ai-news-curator/
├── src/
│   ├── collectors/        # 데이터 수집 (RSS, arXiv, YouTube)
│   ├── source_manager.py  # Notion 기반 동적 소스 관리
│   ├── content_filter.py  # 2단계 필터링 로직
│   ├── summarizers/       # OpenAI 요약 처리
│   ├── sinks/            # Notion, Telegram 출력
│   └── cache_manager.py   # 중복 처리 방지
├── configs/
│   └── sources.yaml      # 폴백용 소스 설정
└── .github/workflows/    # GitHub Actions 스케줄링
```

핵심은 **동적 소스 관리 시스템**이다. 하드코딩된 설정 대신 Notion에서 소스를 관리하고 실시간으로 반영할 수 있도록 구현했다.

## 혁신적 소스 관리 시스템

### Notion 기반 동적 소스 관리

기존 방식의 한계:
- YAML 파일에 하드코딩된 소스 목록
- 새 소스 추가시 코드 배포 필요
- 카테고리별 관리 어려움

해결책으로 **HybridSourceManager**를 구현했다:

```python
class HybridSourceManager:
    def __init__(self, notion_secret: str, notion_db_id: str):
        self.notion_manager = NotionSourceManager(notion_secret, notion_db_id)
        
    def get_all_sources(self) -> Dict[str, List[SourceConfig]]:
        """Notion 우선, YAML 폴백 방식"""
        sources_by_category = {
            'website': [], 'newsletter': [], 'youtube': [],
            'twitter': [], 'threads': [], 'arxiv': []
        }
        
        # 1. Notion에서 소스 가져오기
        if self.notion_manager:
            notion_sources = self.notion_manager.fetch_sources()
            for source in notion_sources:
                if source.category in sources_by_category:
                    sources_by_category[source.category].append(source)
        
        # 2. YAML 폴백 (Notion 실패시)
        if all(len(v) == 0 for v in sources_by_category.values()):
            sources_by_category = self._load_from_yaml()
        
        return sources_by_category
```

### Notion 데이터베이스 구조

소스 관리를 위한 Notion DB 스키마:

| 속성 | 타입 | 설명 |
|------|------|------|
| Name | Title | 소스 이름 |
| URL | URL | RSS/웹사이트 URL |
| Category | Select | website, newsletter, youtube, twitter, threads |
| SubCategory | Select | ai_research, tech_news, startup |
| MaxItems | Number | 최대 수집 개수 |
| Priority | Number | 우선순위 (1-10) |
| Enabled | Checkbox | 활성화 여부 |

### 동적 소스 로딩

운영 중 코드 변경 없이 소스를 추가/제거할 수 있다:

```python
def fetch_sources(self) -> List[SourceConfig]:
    response = self.client.databases.query(
        database_id=self.database_id,
        filter={
            "property": "Enabled",
            "checkbox": {"equals": True}
        }
    )
    
    sources = []
    for page in response.get('results', []):
        properties = page['properties']
        sources.append(SourceConfig(
            name=self._get_text_property(properties, 'Name'),
            url=self._get_url_property(properties, 'URL'),
            category=self._get_select_property(properties, 'Category'),
            max_items=self._get_number_property(properties, 'MaxItems', 5),
            priority=self._get_number_property(properties, 'Priority', 1),
            enabled=self._get_checkbox_property(properties, 'Enabled', True)
        ))
    
    return sources
```

## 데이터 수집 구현

### 다중 소스 병렬 수집

ThreadPoolExecutor로 여러 소스를 동시에 처리한다:

```python
def fetch_many(feed_urls: List[str]) -> List[RssItem]:
    all_items = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {
            executor.submit(fetch_one, url): url 
            for url in feed_urls
        }
        for future in as_completed(future_to_url):
            items = future.result()
            if items:
                all_items.extend(items)
    return all_items
```

### 특수 소스 처리

**YouTube 채널**: 숨겨진 RSS 엔드포인트 활용
```
https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}
```

**arXiv 논문**: 전용 파이썬 라이브러리 사용
```python
def query_arxiv(search_query: str, max_results: int = 10):
    search = arxiv.Search(
        query=search_query,  # "cat:cs.AI OR cat:cs.LG"
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    return [create_arxiv_item(result) for result in search.results()]
```

## 지능형 콘텐츠 필터링

### 2단계 필터링 전략

하루 200개 이상의 뉴스를 모든 GPT로 처리하면 비용이 과도하다. 2단계 접근법으로 해결:

**1단계: 키워드 기반 스마트 필터링**
```python
def simple_keyword_filter(items: List, max_items: int = 50) -> List:
    # 핵심 기술 트렌드 키워드 (최고 점수)
    tech_trend_keywords = [
        'GPT-5', 'GPT-6', 'Claude', 'Gemini', 'LLM', 'transformer',
        'AGI', 'multimodal', 'robotics', 'autonomous'
    ]
    
    # 연구 & 혁신 키워드 (높은 점수)  
    research_keywords = [
        'research', 'breakthrough', 'innovation', 'discovery',
        'benchmark', 'state-of-the-art', 'SOTA'
    ]
    
    # 날짜 기반 가중치
    cutoff_date = datetime.now() - timedelta(days=30)
    
    for item in items:
        score = 0.0
        
        # 키워드 점수
        text = f"{item.title} {item.content}".lower()
        for keyword in tech_trend_keywords:
            if keyword.lower() in text:
                score += 10
                
        # 최신성 점수  
        if item.published_date > cutoff_date:
            days_old = (datetime.now() - item.published_date).days
            if days_old <= 1:
                score += 15
            elif days_old <= 7:
                score += 10
                
        item.score = score
    
    return sorted(items, key=lambda x: x.score, reverse=True)[:max_items]
```

**2단계: GPT-3.5 정밀 평가**

상위 50개만 AI로 정밀 평가한다:
```python
def get_filtered_items(api_key: str, items: List, max_items: int = 20):
    # 1단계: 키워드 필터링
    pre_filtered = simple_keyword_filter(items, 50)
    
    # 2단계: AI 평가
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
다음 {len(pre_filtered)}개 뉴스를 평가하여 상위 {max_items}개를 선별하라.

평가 기준:
1. 기술적 혁신성 (새로운 기술, 방법론, 아이디어)
2. 실용성 (실제 적용 가능성, 상용화 잠재력)  
3. 영향력 (업계/사회에 미칠 파급효과)
4. 시의성 (최신 트렌드와의 연관성)

각 항목을 0-10점으로 평가하고 상위 {max_items}개만 선별하라.
결과는 JSON 배열로 반환: [{{"index": 1, "score": 8.5, "reason": "이유"}}]

{format_items_for_prompt(pre_filtered)}
"""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    # JSON 파싱 및 결과 반환
    return parse_ai_results(response, pre_filtered)
```

이 방식으로 API 비용을 **95% 절감**했다.

## 요약 시스템

### 한국어 한줄 요약

GPT-4o-mini로 각 뉴스를 한 문장으로 요약한다:

```python
def summarize(api_key: str, title: str, url: str, text: str) -> Summary:
    client = OpenAI(api_key=api_key)
    
    prompt = f"""다음 기술 뉴스를 한국어로 한 문장으로 요약해주세요.

제목: {title}
본문: {text[:5000]}

요약 규칙:
1. 반드시 한 문장으로 작성 (마침표 하나만)
2. 가장 중요한 핵심 정보만 포함  
3. 구체적인 제품명, 기술명, 수치가 있다면 포함
4. 50-100자 이내로 간결하게
5. "~했다", "~발표했다", "~출시했다" 등 명확한 동사로 종료

예시:
- OpenAI가 GPT-4 Turbo를 출시하며 128K 컨텍스트 윈도우와 30% 저렴한 가격을 발표했다.
- Google이 Gemini 1.5 Pro에서 100만 토큰 처리 능력을 시연했다."""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # 비용 효율적
        messages=[
            {"role": "system", "content": "You are a concise tech news summarizer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=150
    )
    
    return Summary(
        title=title,
        url=url, 
        summary=response.choices[0].message.content.strip()
    )
```

### 병렬 요약 처리

ThreadPoolExecutor + 스마트 캐싱으로 성능 최적화:

```python
def summarize_items_parallel(api_key: str, items: List, max_workers: int = 5):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 캐시 확인
        cache_keys = [hash(item.link) for item in items]
        cached_results = {
            key: content_cache.get(key) 
            for key in cache_keys 
            if content_cache.exists(key)
        }
        
        # 캐시되지 않은 항목만 처리
        items_to_process = [
            item for item, key in zip(items, cache_keys)
            if key not in cached_results
        ]
        
        # 병렬 요약
        future_to_item = {
            executor.submit(summarize, api_key, item.title, item.link, item.content): item
            for item in items_to_process
        }
        
        # 결과 수집 및 캐싱
        for future in as_completed(future_to_item):
            result = future.result()
            if result:
                content_cache.set(hash(result.url), result, ttl=7*24*3600)  # 7일 캐시
```

순차 처리 5분 → 병렬 처리 1분 30초로 **70% 시간 단축**.

## 외부 API 연동

### Notion API 통합

**Database ID 포맷 이슈**: URL 복사시와 API 요구 형식이 다르다
```python
def _format_database_id(self, database_id: str) -> str:
    # UUID 형식으로 변환 (8-4-4-4-12)
    clean_id = database_id.replace("-", "")
    if len(clean_id) == 32:
        return f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
    return database_id
```

**Rate Limiting 처리**: 초당 3개 요청 제한
```python
def create_page_with_retry(self, properties, max_retries=3):
    for attempt in range(max_retries):
        try:
            return self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
        except APIResponseError as e:
            if e.code == "rate_limited" and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # exponential backoff
                time.sleep(wait_time)
            else:
                raise
```

### Telegram Bot 연동

python-telegram-bot 대신 requests를 직접 사용했다. 더 가볍고 안정적이었다:

```python
class TelegramSink:
    def __init__(self, bot_token: str, chat_id: str):
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._api_url = f"https://api.telegram.org/bot{bot_token}"

    def _send_message(self, text: str) -> bool:
        try:
            url = f"{self._api_url}/sendMessage"
            data = {
                'chat_id': self._chat_id,
                'text': text,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"전송 실패: {e}")
            return False

    def send_digest(self, title: str, items: List, max_items: int = 20):
        """상위 20개 뉴스를 개별 메시지로 전송"""
        for i, item in enumerate(items[:max_items], 1):
            message = f"📰 *{i}. {item.source}*\n"
            message += f"**{item.title}**\n\n"
            message += f"{item.summary}\n\n"
            message += f"🔗 [원문 보기]({item.link})"
            
            self._send_message(message)
```

#### 개인 채팅 vs 그룹 채팅 지원

텔레그램 봇은 개인 채팅과 그룹 모두에서 작동한다:

**개인 채팅 설정:**
- Chat ID: 양수 (예: `7436611601`)
- 봇이 개인 메시지로 뉴스 전송

**그룹 채팅 설정:**
- Chat ID: 음수 (예: `-4758384327`)
- 그룹에 봇 초대 후 그룹 전체가 뉴스 수신
- Admin 권한 불필요 (메시지 전송만 하므로)

그룹 Chat ID 확인을 위한 전용 도구도 개발했다:

```python
def get_chat_id(bot_token):
    """봇이 추가된 모든 채팅의 Chat ID 조회"""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    response = requests.get(url)
    data = response.json()
    
    for update in data.get('result', []):
        chat = update.get('message', {}).get('chat', {})
        chat_type = chat.get('type')
        
        if chat_type == 'group':
            print(f"👥 그룹 채팅")
            print(f"   Chat ID: {chat.get('id')}")
            print(f"   그룹명: {chat.get('title')}")
```

## 자동화 구현

### GitHub Actions 스케줄링

매일 자정 UTC (한국시간 오전 9시)에 자동 실행:

```yaml
name: Daily AI News Curator
on:
  schedule:
    - cron: '0 0 * * *'  # 매일 자정 UTC
  workflow_dispatch:      # 수동 실행 가능

jobs:
  run-curator:
    runs-on: ubuntu-latest
    environment: OPENAI_API_KEY  # Environment secrets 사용
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run AI News Curator
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        NOTION_INTEGRATION_SECRET: ${{ secrets.NOTION_INTEGRATION_SECRET }}
        NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
        NOTION_SOURCE_DATABASE_ID: ${{ secrets.NOTION_SOURCE_DATABASE_ID }}
        TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
      run: python -m src.main
```

GitHub의 무료 2000분/월로 충분하다. 서버 비용 없이 완전 자동화 달성.

## 운영 결과

### 성과 측정

3주간 운영 결과:
- **시간 절약**: 매일 30-60분 → 5분 (94% 절약)
- **비용**: 하루 $0.044 (월 $1.32)
- **정확도**: 중요 뉴스 누락 0건
- **처리량**: 일 평균 200개 수집 → 20개 선별
- **소스 관리**: 54개 소스를 Notion에서 동적 관리
- **알림 방식**: 개인 → 그룹 채팅으로 확장 (Column Studio 그룹)

### AI 필터링 품질

실제로 기술적 가치가 높은 콘텐츠를 잘 선별했다:
- Stability AI의 새 확산 모델 논문
- OpenAI의 경제적 영향 연구  
- Berkeley AI Lab의 Prompt Injection 방어 기법
- Anthropic의 Constitutional AI 발전

단순 키워드 매칭이 아닌 맥락 이해 기반 선별이 효과적이었다.

### Notion 소스 관리의 장점

운영 중 확인한 핵심 이점들:
- **무중단 소스 추가**: 코드 배포 없이 새 소스 즉시 반영
- **카테고리별 관리**: website, newsletter, youtube 등 체계적 분류
- **우선순위 조절**: 중요 소스에 높은 priority 부여
- **활성화 토글**: 일시적으로 소스 비활성화 가능
- **시각적 관리**: Notion UI로 직관적 소스 현황 파악

## 교훈과 인사이트

### 성공한 기술적 선택

**동적 소스 관리**: 하드코딩된 YAML에서 Notion DB로 이전한 것이 가장 혁신적이었다. 운영 중 유연한 소스 관리가 가능해졌다.

**2단계 필터링**: GPT-4로 모든 콘텐츠를 처리하려다가 비용 문제로 포기. 키워드 + GPT-3.5 조합으로 95% 비용 절감하면서 품질 유지.

**병렬 처리 + 캐싱**: ThreadPoolExecutor와 7일 TTL 캐시로 성능과 비용을 동시에 최적화했다.

**모듈화된 설계**: 각 컴포넌트를 독립적으로 구현해 YouTube 수집기 같은 새 기능을 기존 코드 수정 없이 추가할 수 있었다.

### 개선 필요한 부분

**테스트 코드 부재**: 빠른 개발에 집중하다 테스트를 생략했다. Notion API 통합에서 예상치 못한 버그가 프로덕션에서 발견됐다.

**YouTube API 불안정성**: 트랜스크립트 API가 간헐적으로 실패한다. 폴백 메커니즘 구현이 필요하다.

**필터링 투명성**: AI가 특정 콘텐츠를 선택한 근거가 불명확하다. 선별 이유를 함께 저장하는 기능이 필요하다.

**봇 관리 도구의 필요성**: 그룹 Chat ID 확인, 봇 상태 점검 등의 운영 도구가 추가로 필요했다. `get_group_chat_id.py`와 `check_bot_status.py` 도구를 개발해 해결했다.

### 핵심 인사이트

**완벽함보다 실용성**: 100% 정확도를 목표로 했으나, 80% 정확도로도 충분한 가치를 제공했다. 매일 30분 절약으로 연간 180시간 확보 가능.

**외부 도구 활용**: Notion을 단순 저장소가 아닌 설정 관리 플랫폼으로 활용한 것이 혁신적이었다. 기존 도구의 새로운 활용법을 모색하라.

**점진적 개선**: MVP로 시작해 사용하면서 개선해나가는 접근이 효과적이었다. 완벽한 시스템을 처음부터 만들려 하지 말라.

## 정리

3주간 AI 뉴스 큐레이터 개발로 얻은 핵심 성과:

### 기술 스택
```
Data Sources: RSS + arXiv + YouTube (54개 소스)
Source Management: Notion Database (동적 관리)
Filtering: Keyword + GPT-3.5-turbo
Summarization: GPT-4o-mini (한국어 한줄 요약)
Storage: Notion API
Notification: Telegram Bot (개인/그룹 지원, 20개 뉴스)
Automation: GitHub Actions (무료 크론)
Management Tools: Chat ID 확인, 봇 상태 점검
```

### 핵심 혁신사항
1. **동적 소스 관리**: Notion DB 기반 실시간 소스 관리
2. **2단계 필터링**: 비용 효율적 AI 활용법
3. **병렬 처리**: ThreadPoolExecutor + 스마트 캐싱  
4. **완전 자동화**: GitHub Actions로 서버 비용 0원
5. **유연한 알림**: 개인/그룹 채팅 모두 지원하는 텔레그램 봇

### 운영 성과
- 시간 절약: 94% (연간 180시간)
- 비용: 월 $1.32 저비용 운영  
- 정확도: 중요 뉴스 누락 0건
- 확장성: 코드 변경 없이 소스 추가/제거
- 사용자 확장: 개인 → 그룹(Column Studio) 전환으로 다수 수혜

전체 코드는 [GitHub](https://github.com/LimJih00n/ai-news-curator)에 공개되어 있다. 특히 `source_manager.py`의 동적 소스 관리 시스템을 참고하면 다른 자동화 프로젝트에도 응용할 수 있을 것이다.

**완벽한 시스템보다 작동하는 시스템을 먼저 만들어라.** 그리고 외부 도구를 창의적으로 활용해 더 큰 가치를 창출하라.