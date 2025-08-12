from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import os

from openai import OpenAI


@dataclass
class Summary:
    title: str
    url: str
    summary: str


def summarize(openai_api_key: str, title: str, url: str, text: str, language: str = "ko") -> Summary:
    client = OpenAI(api_key=openai_api_key)
    
    # 한줄 요약 프롬프트
    prompt = f"""다음 기술 뉴스를 한국어로 한 문장으로 요약해주세요.

제목: {title}
URL: {url}

본문:
{text[:5000]}

요약 규칙:
1. 반드시 한 문장으로 작성 (마침표 하나만)
2. 가장 중요한 핵심 정보만 포함
3. 구체적인 제품명, 기술명, 수치가 있다면 포함
4. 50-100자 이내로 간결하게
5. "~했다", "~발표했다", "~출시했다" 등 명확한 동사로 종료

예시:
- OpenAI가 GPT-4 Turbo를 출시하며 128K 컨텍스트 윈도우와 30% 저렴한 가격을 발표했다.
- Google이 Gemini 1.5 Pro에서 100만 토큰 처리 능력을 시연했다.
- Anthropic이 Claude 3.5 Sonnet으로 GPT-4를 능가하는 코딩 성능을 달성했다."""
    
    resp = client.chat.completions.create(
        model="gpt-4o-mini",  # 비용 효율적인 모델 사용
        messages=[
            {"role": "system", "content": "You are a concise tech news summarizer. Create one-sentence summaries in Korean that capture the most important information."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=150,  # 한줄 요약이므로 토큰 수 감소
    )
    content = resp.choices[0].message.content or ""
    return Summary(title=title, url=url, summary=content.strip())
