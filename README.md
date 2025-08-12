# 🤖 AI News Curator

**매일 아침 9시, 큐레이션된 AI/IT 뉴스를 자동으로 받아보세요!**

AI가 50개 이상의 소스에서 수백 개의 뉴스를 수집하고, 중요도에 따라 상위 20개만 선별하여 한국어로 요약해드립니다. Notion과 텔레그램으로 자동 전송되어 더 이상 뉴스 사이트를 돌아다닐 필요가 없습니다.

## ✨ 주요 기능

- **🔄 자동화**: 매일 오전 9시 GitHub Actions로 자동 실행
- **🧠 AI 필터링**: GPT를 활용해 중요한 뉴스만 선별 (상위 20개)
- **📝 한국어 요약**: 각 뉴스를 3-5줄로 간결하게 요약
- **📱 다중 출력**: Notion 데이터베이스 + 텔레그램 봇
- **🔧 외부 소스 관리**: Notion에서 뉴스 소스를 동적으로 관리
- **⚡ 병렬 처리**: 빠른 수집과 요약을 위한 최적화

## 📊 데이터 소스 (54개)

### 🌐 주요 IT 미디어
- TechCrunch, The Verge, Wired, MIT Technology Review
- Hacker News, Reddit (r/MachineLearning, r/LocalLLaMA)
- 요즘IT, 유나이티드 스타트업스

### 🏢 AI 기업 블로그
- OpenAI, Anthropic, Google AI, DeepMind
- Hugging Face, Stability AI
- 네이버 D2, 카카오 Tech Blog

### 🎓 연구 기관
- arXiv (cs.AI, cs.LG, cs.CL, cs.CV 등)
- Stanford AI Lab, Berkeley AI Research

### 📺 YouTube 채널
- Two Minute Papers, Yannic Kilcher
- AI Explained, Machine Learning Street Talk

### 📰 뉴스 검색
- Google News (GPT, AI, machine learning 키워드)

## 🚀 빠른 시작

### 1. 저장소 Fork 및 복사

```bash
git clone https://github.com/YOUR_USERNAME/ai-news-curator.git
cd ai-news-curator
```

### 2. 환경 설정

필수 API 키들을 준비하세요:

- **OpenAI API Key**: [OpenAI Platform](https://platform.openai.com/api-keys)에서 발급
- **Notion Integration**: [Notion Developers](https://developers.notion.com/)에서 생성
- **Telegram Bot**: [@BotFather](https://t.me/BotFather)에게 `/newbot` 명령어로 생성

### 3. GitHub Secrets 설정

GitHub 저장소의 `Settings > Secrets and variables > Actions`에서 다음 secrets를 추가:

```
OPENAI_API_KEY=sk-proj-...
NOTION_INTEGRATION_SECRET=ntn_...
NOTION_DATABASE_ID=your-database-id
NOTION_SOURCE_DATABASE_ID=your-source-database-id
TELEGRAM_BOT_TOKEN=1234567890:ABC...
TELEGRAM_CHAT_ID=your-chat-id
```

### 4. Notion 설정

#### 뉴스 출력용 데이터베이스 생성:
다음 속성을 가진 Notion 데이터베이스를 생성하세요:
- `Name` (Title)
- `Summary` (Text)
- `Link` (URL)
- `Source` (Text)
- `Tags` (Multi-select)

#### 소스 관리용 데이터베이스 생성:
다음 속성을 가진 Notion 데이터베이스를 생성하세요:
- `NAME` (Title): 소스 이름
- `URL` (URL): RSS/웹사이트 URL
- `Type` (Select): website, newsletter, youtube, twitter, threads
- `Active` (Checkbox): 활성화 여부
- `Max Items` (Number): 최대 수집 개수

### 5. 자동화 활성화

GitHub Actions는 자동으로 활성화됩니다:
- **매일 오전 9시 (한국시간)** 자동 실행
- Actions 탭에서 수동 실행도 가능

## 📱 사용법

### 자동 모드
설정 완료 후 아무것도 할 필요가 없습니다. 매일 아침 9시에:
1. 50개+ 소스에서 뉴스 수집
2. AI가 상위 20개 선별
3. 한국어로 요약
4. Notion에 저장
5. 텔레그램으로 전송

### 수동 실행
GitHub Actions에서 "Run workflow" 버튼으로 즉시 실행 가능

### 로컬 개발
```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\\Scripts\\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# .env 파일 생성
cp configs/.env.sample .env
# .env 파일에 API 키들 입력

# 실행
python -m src.main
```

## ⚙️ 설정 옵션

### 환경 변수

| 변수명 | 필수 | 기본값 | 설명 |
|--------|------|--------|------|
| `OPENAI_API_KEY` | ✅ | - | OpenAI API 키 |
| `NOTION_INTEGRATION_SECRET` | ❌ | - | Notion Integration 토큰 |
| `NOTION_DATABASE_ID` | ❌ | - | 뉴스 출력용 Notion DB ID |
| `NOTION_SOURCE_DATABASE_ID` | ❌ | - | 소스 관리용 Notion DB ID |
| `TELEGRAM_BOT_TOKEN` | ❌ | - | 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | ❌ | - | 텔레그램 채팅 ID |
| `MAX_FILTERED_ITEMS` | ❌ | 20 | 선별할 뉴스 개수 |
| `MAX_WORKERS` | ❌ | 5 | 병렬 처리 워커 수 |
| `ENABLE_CACHE` | ❌ | true | 캐싱 활성화 |

### 소스 관리

Notion 소스 데이터베이스에서 뉴스 소스를 동적으로 관리할 수 있습니다:
- 새 소스 추가/제거
- 타입별 분류 (website, newsletter, youtube 등)
- 활성화/비활성화
- 수집 개수 제한

## 🛠️ 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  AI Processing   │───▶│    Outputs      │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ • RSS Feeds     │    │ • Content Filter │    │ • Notion DB     │
│ • arXiv Papers  │    │ • Summarization  │    │ • Telegram Bot  │
│ • YouTube       │    │ • Translation    │    │ • Markdown      │
│ • Reddit        │    │ • Ranking        │    │                 │
│ • Google News   │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 핵심 컴포넌트

- **Collectors**: 다양한 소스에서 데이터 수집
- **Filters**: 키워드 + AI 기반 2단계 필터링
- **Summarizers**: GPT-4o-mini를 사용한 한국어 요약
- **Sinks**: Notion, Telegram 등 다중 출력
- **Cache**: 중복 처리 방지 및 성능 최적화

## 📈 성능 최적화

- **2단계 필터링**: 키워드 → AI 필터링으로 API 비용 95% 절감
- **병렬 처리**: ThreadPoolExecutor로 5배 속도 향상
- **스마트 캐싱**: 7일 TTL 캐시로 중복 요약 방지
- **날짜 기반 우선순위**: 최신 콘텐츠에 높은 가중치

## 💰 비용

- **일일 운영비**: 약 $0.044 (월 $1.32)
- **GitHub Actions**: 2000분/월 무료 (충분함)
- **API 호출**: GPT-3.5 필터링 + GPT-4o-mini 요약

## 🔧 커스터마이징

### 새 데이터 소스 추가
```python
# src/collectors/your_collector.py
def fetch_your_source():
    # 구현
    return items
```

### 요약 스타일 변경
```python
# src/summarizers/openai_summarizer.py
# 프롬프트 수정으로 요약 스타일 커스터마이징
```

### 출력 채널 추가
```python
# src/sinks/your_sink.py
class YourSink:
    def send_digest(self, items):
        # 구현
```

## 🐛 문제 해결

### 일반적인 문제들

**Q: GitHub Actions에서 "secrets not found" 오류**
A: Settings > Secrets에서 모든 required secrets이 설정되었는지 확인

**Q: Notion 연동이 안 됨**
A: Integration이 해당 데이터베이스에 권한을 가지고 있는지 확인

**Q: 텔레그램 메시지가 오지 않음**
A: Bot을 채팅방에 추가하고 CHAT_ID가 정확한지 확인

**Q: 요약 품질이 아쉬움**
A: `src/summarizers/openai_summarizer.py`에서 프롬프트 수정

### 디버깅
```bash
# 로컬에서 실행하여 상세 로그 확인
python -m src.main
```

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 라이선스

MIT License - 자유롭게 사용하고 수정하세요.

## 🙏 감사의 말

이 프로젝트는 매일 뉴스 사이트를 순회하는 시간을 절약하고, AI의 힘으로 정말 중요한 정보만 골라받고자 하는 마음에서 시작되었습니다. 

**매일 30분씩 절약하면, 한 달이면 15시간, 1년이면 180시간을 확보할 수 있습니다.**

여러분의 소중한 시간이 더 의미있는 곳에 쓰이길 바랍니다. 🚀

---

**⭐ 도움이 되셨다면 Star를 눌러주세요!**