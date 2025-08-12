# 외부 소스 관리 시스템

AI News Curator는 이제 Notion을 통한 동적 소스 관리를 지원합니다. 더 이상 YAML 파일을 수정할 필요 없이 Notion 데이터베이스에서 직접 뉴스 소스를 관리할 수 있습니다.

## 주요 기능

- **동적 소스 관리**: Notion 데이터베이스에서 실시간으로 소스 추가/수정/삭제
- **카테고리별 분류**: website, newsletter, youtube, twitter, threads 등으로 소스 분류
- **우선순위 설정**: 1-10 스케일로 소스별 중요도 설정
- **자동 폴백**: Notion 연결 실패 시 자동으로 YAML 파일 사용

## 설정 방법

### 1. Notion Integration 생성

1. [Notion Integrations](https://www.notion.so/my-integrations) 페이지 접속
2. "New integration" 클릭
3. Integration 이름 입력 (예: "AI News Curator")
4. 생성 후 "Internal Integration Secret" 복사

### 2. Notion 데이터베이스 생성

1. Notion에서 새 페이지 생성
2. Table 데이터베이스 추가
3. 다음 속성(Properties) 추가:

| 속성명 | 타입 | 설명 | 필수 |
|--------|------|------|------|
| Name | Title | 소스 이름 | ✅ |
| URL | URL | RSS/웹사이트 URL | ✅ |
| Category | Select | 소스 카테고리 | ✅ |
| SubCategory | Select | 세부 카테고리 | ❌ |
| MaxItems | Number | 최대 수집 개수 | ❌ |
| Priority | Number | 우선순위 (1-10) | ❌ |
| Enabled | Checkbox | 활성화 여부 | ✅ |
| LastUpdated | Date | 마지막 업데이트 | ❌ |
| Notes | Text | 메모 | ❌ |

#### Category 옵션:
- `website`: 일반 웹사이트/블로그
- `newsletter`: 뉴스레터
- `youtube`: YouTube 채널
- `twitter`: Twitter/X 계정
- `threads`: Threads 계정
- `arxiv`: arXiv 논문

#### SubCategory 옵션:
- `ai_research`: AI 연구
- `tech_news`: 기술 뉴스
- `startup`: 스타트업
- `general`: 일반

### 3. Integration 연결

1. 생성한 데이터베이스 페이지에서 우측 상단 "..." 메뉴 클릭
2. "Connections" 또는 "연결" 선택
3. 생성한 Integration 검색 및 추가

### 4. 환경 변수 설정

`.env` 파일에 다음 추가:

```env
# Notion 소스 관리 (선택사항)
NOTION_SOURCE_DATABASE_ID=your_database_id_here
NOTION_SOURCE_INTEGRATION_SECRET=your_integration_secret_here
```

데이터베이스 ID 찾기:
- 데이터베이스 URL: `https://notion.so/workspace/24d6b8f0bbee80dcb749da270d6defcf?v=...`
- 데이터베이스 ID: `24d6b8f0bbee80dcb749da270d6defcf`

### 5. 초기 설정 실행

```bash
python setup_notion_sources.py
```

이 스크립트는:
- Notion 연결 테스트
- 데이터베이스 구조 확인
- 샘플 소스 추가 (선택사항)

## 소스 추가 방법

### Notion에서 직접 추가

1. Notion 데이터베이스 열기
2. "New" 버튼 클릭
3. 다음 정보 입력:
   - **Name**: 소스 이름 (예: "OpenAI Blog")
   - **URL**: RSS 피드 URL
   - **Category**: 카테고리 선택
   - **MaxItems**: 수집할 최대 항목 수 (기본값: 5)
   - **Priority**: 1-10 (높을수록 우선)
   - **Enabled**: 체크 (활성화)

### YouTube 채널 추가

YouTube 채널 ID를 RSS URL로 변환:
```
https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
```

예시:
- Two Minute Papers: `https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg`

### RSS 피드 찾기

대부분의 블로그와 뉴스 사이트는 RSS를 제공합니다:
- 도메인 + `/feed` 또는 `/rss`
- 도메인 + `/atom.xml`
- 브라우저 확장 프로그램 사용 (RSS Feed Reader 등)

## 우선순위 가이드

| 우선순위 | 용도 | 예시 |
|----------|------|------|
| 9-10 | 핵심 소스 | OpenAI, Anthropic 공식 블로그 |
| 7-8 | 중요 소스 | 주요 AI 연구 기관, 유명 뉴스레터 |
| 5-6 | 일반 소스 | 기술 뉴스, 업계 블로그 |
| 3-4 | 보조 소스 | 개인 블로그, 특정 주제 |
| 1-2 | 낮은 우선순위 | 가끔 확인하는 소스 |

## 작동 방식

1. **Notion 우선**: 프로그램 실행 시 먼저 Notion 데이터베이스에서 소스를 로드
2. **자동 폴백**: Notion 연결 실패 시 `configs/sources.yaml` 파일 사용
3. **캐싱**: 수집된 콘텐츠는 7일간 캐시되어 중복 수집 방지
4. **병렬 처리**: 여러 소스를 동시에 수집하여 속도 향상

## 문제 해결

### Notion 연결 실패
- Integration Secret 확인
- 데이터베이스 ID 확인
- Integration이 데이터베이스에 연결되었는지 확인

### 소스가 수집되지 않음
- URL이 올바른 RSS/Atom 피드인지 확인
- Enabled 체크박스가 활성화되어 있는지 확인
- MaxItems가 0이 아닌지 확인

### 오래된 콘텐츠가 수집됨
- 캐시 삭제: `rm -rf cache/`
- RSS 피드 자체가 오래된 콘텐츠를 제공하는지 확인

## 고급 설정

### 하이브리드 모드

Notion과 YAML을 동시에 사용:
1. Notion에 주요 소스 등록
2. `configs/sources.yaml`에 백업 소스 유지
3. Notion 실패 시 자동으로 YAML 사용

### 카테고리별 처리

`src/main.py`에서 카테고리별로 다른 처리 가능:
```python
external_sources = source_manager.get_all_sources()

# 웹사이트는 RSS로 수집
for source in external_sources['website']:
    # RSS 수집 로직

# YouTube는 전용 수집기 사용
for source in external_sources['youtube']:
    # YouTube API 사용
```

## 추가 개발 아이디어

- [ ] Twitter/X API 통합
- [ ] Threads API 통합
- [ ] 소스별 수집 주기 설정
- [ ] 소스 건강도 모니터링
- [ ] 자동 소스 추천 시스템
- [ ] 소스별 성과 분석 (클릭률, 관련성 등)