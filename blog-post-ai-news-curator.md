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
- **OpenAI API**: GPT-3.5 (필터링) + GPT-4o-mini (요약)
- **Notion API**: 결과 저장
- **Telegram Bot API**: 실시간 알림
- **GitHub Actions**: 무료 크론 서비스

### 시스템 아키텍처

모듈화된 구조로 설계했다:
```
ai-news-curator/
├── src/
│   ├── collectors/      # 데이터 수집 (RSS, arXiv, YouTube)
│   ├── filters/         # 2단계 필터링 로직
│   ├── summarizers/     # OpenAI 요약 처리
│   ├── sinks/          # Notion, Telegram 출력
│   └── cache/          # 중복 처리 방지
├── configs/
│   └── sources.yaml    # 데이터 소스 설정
└── .github/workflows/  # GitHub Actions 스케줄링
```

각 컴포넌트는 독립적으로 테스트 가능하도록 설계했다. 나중에 새로운 소스나 출력 채널을 추가하기 쉽게 하기 위함이다.

## 데이터 수집 구현

### RSS 수집의 한계와 해결책

초기에는 feedparser로 단순하게 RSS를 수집했다:

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

병렬 처리로 속도는 개선됐지만 한계가 있었다:

**YouTube 채널 처리**: YouTube는 공식 RSS를 제공하지 않는다. 하지만 숨겨진 RSS 엔드포인트를 발견했다:
```
https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}
```

**arXiv 논문 수집**: arXiv는 REST API가 아닌 자체 프로토콜을 사용한다. arxiv 파이썬 라이브러리로 해결:

```python
def query_arxiv(search_query: str, max_results: int = 10):
    search = arxiv.Search(
        query=search_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    return [create_arxiv_item(result) for result in search.results()]
```

## AI 필터링 시스템

### 2단계 필터링 전략

하루 200개 이상의 뉴스를 모두 AI로 처리하면 비용이 과도하다. 2단계 필터링으로 해결했다:

**1단계: 키워드 기반 사전 필터링**
```python
def keyword_based_filter(item: RssItem) -> float:
    score = 0.0
    hot_keywords = {
        'gpt': 5, 'claude': 5, 'llm': 4, 'transformer': 3,
        'diffusion': 3, 'multimodal': 4, 'anthropic': 4
    }
    
    text = f"{item.title} {item.content}".lower()
    for keyword, weight in hot_keywords.items():
        if keyword in text:
            score += weight
    
    # 최신성 가중치 추가
    days_old = (datetime.now() - item.published_date).days
    if days_old <= 1:
        score += 10
    elif days_old <= 3:
        score += 7
        
    return score
```

**2단계: GPT-3.5 정밀 필터링**

상위 50개만 GPT-3.5로 평가한다:
```python
def ai_filter(items: List[RssItem], max_items: int = 20):
    prompt = f"""
평가 기준:
- 기술적 혁신성 (새로운 기술, 방법론)
- 실용성 (실제 적용 가능성) 
- 영향력 (업계 파급효과)
- 시의성 (최신 트렌드 연관성)

각 항목을 0-10점으로 평가하고 상위 {max_items}개를 선별하라.

{format_items(items)}
"""
    
    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
```

이 방식으로 API 비용을 **95% 절감**했다.

## 성능 최적화

### 병렬 처리 도입

초기에는 순차 처리로 20개 항목에 5분이 소요됐다. ThreadPoolExecutor로 1분 30초로 단축:

```python
def summarize_items_parallel(items: List, max_workers: int = 5):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 캐시 확인
        cache_keys = [hash(item.link) for item in items]
        cached_results = {
            key: cache.get(key) 
            for key in cache_keys 
            if cache.exists(key)
        }
        
        # 캐시되지 않은 항목만 처리
        items_to_process = [
            item for item, key in zip(items, cache_keys)
            if key not in cached_results
        ]
        
        # 병렬 요약 처리
        future_to_item = {
            executor.submit(summarize_single, item): item
            for item in items_to_process
        }
        
        # 결과 수집 및 캐싱
        for future in as_completed(future_to_item):
            result = future.result()
            if result:
                cache.set(hash(result.link), result, ttl=7*24*3600)
```

### 스마트 캐싱

7일 TTL 캐시로 중복 요약을 방지한다. 개발 중 반복 테스트 시 시간과 비용을 크게 절약했다.

## 외부 API 연동

### Notion API 통합

Notion API에서 만난 주요 이슈들:

**Database ID 포맷 문제**: URL에서 복사한 ID와 API 요구 형식이 다르다:
```python
def _format_database_id(self, database_id: str) -> str:
    # UUID 형식으로 변환 (8-4-4-4-12)
    clean_id = database_id.replace("-", "")
    if len(clean_id) == 32:
        return f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
    return database_id
```

**Rate Limiting**: 초당 3개 요청 제한. Exponential backoff로 해결:
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
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                raise
```

### 텔레그램 봇 연동

python-telegram-bot 라이브러리 대신 requests를 직접 사용했다. 더 가볍고 안정적이었다:
```python
def _send_message(self, text: str) -> bool:
    try:
        url = f"{self._api_url}/sendMessage"
        data = {
            'chat_id': self._chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"전송 실패: {e}")
        return False
```

## 자동화 구현

### GitHub Actions 스케줄링

매일 자정 UTC (한국시간 오전 9시)에 자동 실행되도록 설정:
```yaml
name: Daily AI News Curator
on:
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:

jobs:
  run-curator:
    runs-on: ubuntu-latest
    environment: OPENAI_API_KEY
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run AI News Curator
      run: python -m src.main
```

GitHub의 무료 크론 서비스를 활용해 서버 비용 없이 자동화했다.

## 운영 결과

### 성과 측정

2주간 운영 결과:
- **시간 절약**: 매일 30-60분 → 5분 (94% 절약)
- **비용**: 하루 $0.044 (월 $1.32)
- **정확도**: 중요 뉴스 누락 0건
- **처리량**: 일 평균 200개 수집 → 20개 선별

### AI 필터링 품질

AI가 실제로 기술적 가치가 있는 콘텐츠를 잘 선별했다:
- Stability AI의 새 확산 모델 논문
- OpenAI의 경제적 영향 연구  
- Berkeley AI Lab의 Prompt Injection 방어 기법

단순한 키워드 매칭이 아닌 맥락 이해 기반 선별이 효과적이었다.

## 교훈과 인사이트

### 성공한 선택들

**모듈화된 설계**: 각 컴포넌트를 독립적으로 구현해 새 소스 추가가 용이했다. YouTube 수집기를 나중에 추가할 때 기존 코드 수정 없이 통합 가능했다.

**2단계 필터링**: 초기에 GPT-4로 모든 콘텐츠를 처리하려 했으나 하루 $2 초과. 키워드 + GPT-3.5 조합으로 비용 95% 절감하면서 품질 유지.

**캐싱 시스템**: 7일 TTL 캐시로 중복 처리 방지. 개발 중 반복 테스트 시 시간과 비용을 크게 절약했다.

**외부 소스 관리**: 하드코딩된 YAML에서 Notion DB로 소스 관리 이전. 운영 중 동적으로 소스 추가/제거 가능해졌다.

### 개선 필요한 부분

**테스트 코드 부재**: 빠른 개발에 집중하다 테스트를 생략했다. Notion API 통합에서 예상치 못한 버그가 프로덕션에서 발견됐다.

**YouTube API 불안정성**: 트랜스크립트 API가 간헐적으로 실패한다. 폴백 메커니즘 구현이 필요하다.

**필터링 투명성 부족**: AI가 특정 콘텐츠를 선택한 이유가 불명확하다. 선별 근거를 함께 저장하는 기능이 필요하다.

## 핵심 인사이트

**완벽함보다 실용성**: 100% 정확도를 목표로 했으나, 80% 정확도로도 충분한 가치를 제공했다. 매일 30분 절약으로 연간 180시간 확보 가능.

**비용 최적화**: GPT-4가 더 좋은 결과를 내지만, 적절한 전처리와 프롬프트 엔지니어링으로 GPT-3.5도 충분했다.

**점진적 개선**: MVP로 시작해 사용하면서 개선해나가는 접근이 효과적이었다. 완벽한 시스템을 한 번에 만들려 하지 말고 작동하는 버전을 먼저 만드는 것이 중요하다.

## 정리

2주간 AI 뉴스 큐레이터를 개발하면서 얻은 주요 성과:

- **자동화**: GitHub Actions로 완전 자동화 (서버 비용 0원)
- **효율성**: 매일 30-60분 → 5분으로 시간 단축
- **비용**: 월 $1.32로 저비용 운영
- **품질**: AI 기반 2단계 필터링으로 높은 정확도
- **확장성**: 모듈화된 구조로 새 소스 추가 용이

### 기술 스택 요약
```
Data Collection: RSS + arXiv + YouTube
Filtering: Keyword + GPT-3.5
Summarization: GPT-4o-mini
Storage: Notion API
Notification: Telegram Bot
Automation: GitHub Actions
```

### 다음 단계

앞으로 추가 고려사항:
- 개인화 추천 시스템 (사용자 피드백 학습)
- 더 정교한 중복 제거 로직
- 다국어 지원 확장
- 실시간 트렌드 반영

전체 코드는 [GitHub](https://github.com/LimJih00n/ai-news-curator)에 공개되어 있다. 관심 있는 개발자들이 fork해서 자신만의 큐레이터를 만들어보길 바란다.

**완벽한 시스템보다 작동하는 시스템을 먼저 만들어라.** 그리고 사용하면서 점진적으로 개선해나가라.