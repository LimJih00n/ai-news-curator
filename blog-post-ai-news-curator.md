# 매일 아침 AI 트렌드를 자동으로 수집하는 뉴스 큐레이터, 2주 만에 만든 이야기

## 들어가며

아침에 눈 뜨자마자 하는 일이 뭔가요? 저는 침대에서 스마트폰으로 해커뉴스, Reddit, arXiv를 돌아다니며 밤사이 올라온 AI 소식들을 확인합니다. 그런데 문득 이런 생각이 들더군요. "이거 매일 하는 건데, 자동화할 수 없을까?"

이 글은 Python과 OpenAI API를 활용해 매일 최신 AI/IT 뉴스를 자동으로 수집하고, 중요한 것만 골라내서 Notion에 정리해주는 시스템을 만든 과정을 담았습니다. 특히 수십 개의 RSS 피드와 arXiv 논문 중에서 정말 읽을 가치가 있는 것만 선별하는 AI 필터링 로직을 구현하는 과정이 흥미로웠는데요, 그 과정에서 겪은 시행착오와 해결 방법을 공유하려 합니다.

만약 여러분도 매일 아침 뉴스 사이트를 순회하며 시간을 보내고 있다면, 혹은 AI를 활용한 자동화 프로젝트에 관심이 있다면, 이 글이 도움이 될 겁니다. 2주간의 개발 과정을 통해 하루 30분씩 절약하게 된 방법, 지금부터 시작합니다.

## 왜 이 프로젝트를 시작했나

### 문제: 정보의 홍수 속에서 진짜를 찾기

IT 업계에서 일하다 보면 하루가 멀다 하고 쏟아지는 새로운 소식들에 압도당하기 쉽습니다. OpenAI가 새 모델을 발표했다, Google이 또 다른 AI 도구를 출시했다, 누군가가 혁신적인 오픈소스를 공개했다... 이런 소식들을 놓치면 뒤처지는 것 같고, 다 읽자니 시간이 부족합니다.

제가 매일 확인하던 소스들만 해도 이 정도였습니다:
- Hacker News (하루 수백 개 포스트)
- Reddit의 r/MachineLearning, r/LocalLLaMA
- arXiv (매일 수십 개의 새 논문)
- TechCrunch, The Verge 등 테크 미디어
- OpenAI, Anthropic 등 주요 AI 기업 블로그
- 유튜브의 AI 관련 채널들

이걸 매일 아침 확인하는 데만 30분에서 1시간. 그것도 대충 훑어보는 수준이었죠.

### 목표: 똑똑한 AI 비서 만들기

그래서 세운 목표는 명확했습니다:
1. 매일 자정에 자동으로 모든 소스에서 최신 콘텐츠를 수집
2. AI를 활용해 정말 중요한 것만 필터링 (상위 20개)
3. 각 아이템을 한국어로 요약
4. Notion 데이터베이스에 자동으로 정리

처음엔 단순할 거라 생각했습니다. RSS 파서 붙이고, ChatGPT API로 요약하면 끝 아닌가? 하지만 실제로 만들어보니 생각보다 고려할 게 많더군요.

## 핵심 개발 과정: 2주간의 여정

### 1단계: 기술 스택 선정과 프로젝트 구조 설계

먼저 기술 스택을 정했습니다. 빠르게 프로토타입을 만들고 싶었기 때문에 익숙한 도구들을 선택했습니다:

- **Python 3.11**: 가장 익숙한 언어이자, 데이터 처리에 최적화
- **OpenAI API**: GPT-3.5로 필터링, GPT-4o-mini로 요약
- **Notion API**: 결과물 저장용
- **GitHub Actions**: 매일 자동 실행

프로젝트 구조는 이렇게 잡았습니다:

```
ai-news-curator/
├── src/
│   ├── collectors/      # RSS, arXiv, YouTube 수집기
│   ├── models.py        # 데이터 모델 정의
│   ├── sinks/          # Notion, Telegram 출력
│   └── main.py         # 메인 오케스트레이션
├── configs/
│   └── sources.yaml    # 데이터 소스 설정
└── output/
    └── notes/         # 마크다운 출력
```

각 컴포넌트를 독립적으로 개발하고 테스트할 수 있도록 모듈화했습니다. 나중에 새로운 데이터 소스나 출력 채널을 추가하기 쉽게 하려는 의도였죠.

### 2단계: 데이터 수집 - RSS의 한계와 우회법

처음엔 RSS 피드만으로 충분할 거라 생각했습니다. feedparser 라이브러리로 간단하게 구현:

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

병렬 처리로 여러 피드를 동시에 가져오니 속도가 크게 개선됐습니다. 하지만 문제가 있었습니다:

**문제 1: YouTube는 RSS를 제공하지 않는다**
- Chester Roh(@chester_roh), AI Dot Engineer 같은 핵심 YouTube 채널들의 최신 영상을 가져올 방법이 없었습니다.
- 해결책: YouTube의 숨겨진 RSS 엔드포인트 발견! `https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}`

**문제 2: arXiv API의 복잡성**
- arXiv는 REST API가 아닌 자체 프로토콜을 사용합니다.
- 해결책: arxiv 파이썬 라이브러리 활용

```python
def query_arxiv(search_query: str, max_results: int = 10) -> List[ArxivItem]:
    search = arxiv.Search(
        query=search_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )
    
    items = []
    for result in search.results():
        items.append(ArxivItem(
            title=result.title,
            abstract=result.summary,
            authors=[author.name for author in result.authors],
            categories=result.categories,
            link=result.entry_id
        ))
    return items
```

### 3단계: AI 필터링 - 비용과 품질의 줄타기

수집한 데이터가 하루에 200개가 넘었습니다. 이걸 다 요약하면 API 비용이 어마어마하겠죠. 그래서 2단계 필터링 전략을 도입했습니다:

**1차 필터: 키워드 기반 빠른 필터링**
```python
def keyword_based_filter(item: RssItem) -> float:
    score = 0.0
    
    # 핵심 키워드 가중치
    hot_keywords = {
        'gpt': 5, 'claude': 5, 'gemini': 4,
        'llm': 4, 'transformer': 3,
        'diffusion': 3, 'multimodal': 4
    }
    
    text = f"{item.title} {item.content}".lower()
    for keyword, weight in hot_keywords.items():
        if keyword in text:
            score += weight
    
    # 지역 뉴스나 광고성 콘텐츠 감점
    if any(word in text for word in ['김포', '부동산', '아파트']):
        score -= 10
        
    return score
```

**2차 필터: GPT-3.5를 활용한 정밀 필터링**

키워드로 1차 필터링한 상위 50개 항목만 GPT-3.5에게 평가를 맡겼습니다:

```python
def ai_based_filter(items: List[RssItem], max_items: int = 20):
    prompt = f"""
    다음 뉴스 항목들을 평가해주세요.
    각 항목에 대해 0-10점을 매기고, 이유를 간단히 설명해주세요.
    
    평가 기준:
    - 기술적 혁신성 (새로운 기술, 방법론)
    - 실용성 (실제 적용 가능성)
    - 영향력 (업계에 미칠 영향)
    - 시의성 (최신 트렌드와의 관련성)
    
    {format_items_for_prompt(items)}
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3  # 일관성 있는 평가를 위해 낮은 temperature
    )
```

### 4단계: 병렬 처리로 속도 개선

초기엔 순차적으로 요약을 처리했는데, 20개 항목을 처리하는 데 5분이 넘게 걸렸습니다. ThreadPoolExecutor로 병렬 처리를 도입하니 1분 30초로 단축:

```python
def summarize_items_parallel(items: List, max_workers: int = 5):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 캐시 확인을 먼저 수행
        cache_keys = [hash(item.link) for item in items]
        cached_results = {
            key: cache.get(key) 
            for key in cache_keys 
            if cache.exists(key)
        }
        
        # 캐시되지 않은 항목만 API 호출
        items_to_process = [
            item for item, key in zip(items, cache_keys)
            if key not in cached_results
        ]
        
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

캐싱 시스템도 함께 구현해서 같은 콘텐츠를 반복 요약하지 않도록 했습니다.

### 5단계: Notion 통합의 함정

Notion API는 생각보다 까다로웠습니다. 특히 데이터베이스 ID 형식이 문제였는데요:

```python
def _format_database_id(self, database_id: str) -> str:
    # Notion은 UUID 형식을 요구 (8-4-4-4-12)
    clean_id = database_id.replace("-", "")
    if len(clean_id) == 32:
        return f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
    return database_id
```

URL에서 복사한 ID와 API가 요구하는 형식이 달라서 한참 헤맸습니다. 

또 다른 이슈는 Rate Limiting. Notion API는 초당 3개 요청으로 제한되어 있어서, 대량의 데이터를 한 번에 올리면 에러가 발생합니다. exponential backoff로 해결:

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

## 결과: 매일 아침의 작은 기적

### 완성된 시스템의 하루

이제 매일 자정이 되면:
1. GitHub Actions가 자동으로 스크립트 실행
2. 30개 이상의 소스에서 200여 개 콘텐츠 수집
3. AI가 상위 20개만 선별
4. 각 항목을 3-5줄로 요약
5. Notion 데이터베이스에 자동 업로드

아침에 일어나면 이미 정리된 오늘의 AI 뉴스가 Notion에서 기다리고 있습니다.

### 실제 성과

2주간 운영한 결과:
- **시간 절약**: 매일 30-60분 → 5분 (Notion 확인만)
- **정보의 질**: 놓친 중요 뉴스 0건 (수동 확인 대비)
- **비용**: 하루 약 $0.044 (한 달 $1.32)
- **수집량**: 일 평균 20개 핵심 아이템

특히 인상적이었던 건, AI가 선별한 콘텐츠의 품질이었습니다. 단순히 키워드만 보는 게 아니라, 실제로 기술적 가치가 있는 내용을 잘 골라냈습니다. 예를 들어:

- Stability AI의 새로운 확산 모델 논문
- OpenAI의 경제적 영향 연구 발표
- Berkeley AI Lab의 Prompt Injection 방어 기법

이런 중요한 소식들을 놓치지 않고 캐치할 수 있었습니다.

## 배운 점: 자동화의 진짜 가치

### 잘한 결정들

**1. 모듈화된 설계**
각 수집기를 독립적으로 만든 덕분에 새로운 소스 추가가 정말 쉬웠습니다. YouTube 수집기를 나중에 추가했는데, 기존 코드를 전혀 건드리지 않고도 통합할 수 있었죠.

**2. 2단계 필터링**
처음엔 모든 콘텐츠를 GPT-4로 처리하려 했는데, 비용이 하루 $2를 넘어갔습니다. 키워드 필터링 + GPT-3.5 조합으로 비용을 95% 절감하면서도 품질은 유지했습니다.

**3. 캐싱 시스템**
같은 콘텐츠를 반복 처리하지 않도록 7일 TTL 캐시를 구현한 건 정말 좋은 선택이었습니다. 특히 개발 중 디버깅할 때 시간과 비용을 크게 절약했죠.

### 아쉬웠던 점들

**1. 테스트 코드 부재**
빠르게 만들다 보니 테스트 코드를 작성하지 않았습니다. 결과적으로 Notion API 통합 부분에서 예상치 못한 버그들이 프로덕션에서 발견됐죠.

**2. 과도한 YouTube 의존**
YouTube 트랜스크립트 API가 불안정해서 가끔 실패합니다. 폴백 메커니즘을 미리 구현했어야 했습니다.

**3. 필터링 로직의 투명성**
AI가 왜 특정 콘텐츠를 선택했는지 명확하지 않아서, 가끔 의외의 결과가 나옵니다. 선택 이유를 함께 저장하도록 개선이 필요합니다.

### 핵심 교훈

이 프로젝트를 통해 깨달은 가장 중요한 점은, **완벽한 자동화보다 실용적인 자동화가 낫다**는 것입니다. 

처음엔 100% 정확도를 목표로 했지만, 80% 정확도로도 충분히 가치가 있었습니다. 매일 30분을 절약하는 것만으로도 한 달이면 15시간, 1년이면 180시간을 확보할 수 있으니까요.

또한 AI를 도구로 활용할 때는 **비용 대비 효과**를 항상 고려해야 합니다. GPT-4가 더 좋은 결과를 낼 수 있지만, GPT-3.5로도 충분한 경우가 많습니다. 중요한 건 적절한 프롬프트 엔지니어링과 전처리입니다.

## 마무리: 당신도 할 수 있습니다

지금까지 2주간의 AI 뉴스 큐레이터 개발기를 읽어주셔서 감사합니다. 

이 프로젝트의 전체 코드는 GitHub에 공개되어 있습니다. Fork해서 자신만의 뉴스 소스를 추가하거나, 다른 언어로 요약하도록 수정해보세요. 특히 `configs/sources.yaml` 파일만 수정하면 관심 분야를 쉽게 바꿀 수 있습니다.

혹시 이 프로젝트를 보고 "나도 이런 거 만들어보고 싶다"는 생각이 드신다면, 주저하지 말고 시작하세요. 완벽하지 않아도 괜찮습니다. 저도 처음엔 단순한 RSS 리더로 시작했으니까요.

다음 포스팅에서는 이 시스템에 **개인화 추천 기능**을 추가하는 과정을 다룰 예정입니다. 읽은 기사에 대한 피드백을 학습해서, 점점 더 내 취향에 맞는 뉴스만 골라주는 AI를 만들어볼 계획이죠.

여러분의 정보 과부하는 어떻게 해결하고 계신가요? 댓글로 공유해주시면, 함께 더 나은 방법을 찾아갈 수 있을 것 같습니다.

---

**P.S.** 이 글을 쓰는 동안에도 제 뉴스 큐레이터는 열심히 새로운 AI 소식들을 수집하고 있습니다. 방금 Anthropic의 새로운 논문이 올라왔다는 알림이 왔네요. 이제 저는 그저 읽기만 하면 됩니다. 😊