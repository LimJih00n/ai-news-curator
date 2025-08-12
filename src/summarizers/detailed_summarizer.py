from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import os

from openai import OpenAI


@dataclass
class DetailedSummary:
    title: str
    url: str
    brief_summary: str      # 한줄 요약 (텔레그램용)
    detailed_summary: str   # 상세 요약 (노션용)


def create_detailed_summary(openai_api_key: str, title: str, url: str, text: str, brief_summary: str) -> DetailedSummary:
    """기존 한줄 요약을 기반으로 상세 요약 생성"""
    client = OpenAI(api_key=openai_api_key)
    
    # 상세 요약 프롬프트
    prompt = f"""다음 기술 뉴스를 한국어로 상세하게 요약해주세요.

제목: {title}
URL: {url}
기존 한줄 요약: {brief_summary}

본문:
{text[:8000]}

상세 요약 규칙:
1. 2-4 문장으로 구성
2. 기존 한줄 요약보다 구체적인 정보 포함
3. 기술적 배경, 의미, 영향을 설명
4. 구체적인 수치, 기능, 특징이 있다면 포함
5. 200-400자 이내로 작성
6. 전문적이면서도 이해하기 쉽게

예시:
한줄: "OpenAI가 GPT-4 Turbo를 출시하며 128K 컨텍스트 윈도우와 30% 저렴한 가격을 발표했다."

상세: "OpenAI가 개발자 컨퍼런스에서 GPT-4 Turbo를 공식 발표했다. 새 모델은 기존 8K 토큰에서 128K 토큰으로 16배 확장된 컨텍스트 윈도우를 지원하며, 약 300페이지 분량의 문서를 한 번에 처리할 수 있다. 가격은 기존 GPT-4 대비 입력 토큰당 3배, 출력 토큰당 2배 저렴하게 책정되어 API 사용 비용을 크게 절감할 수 있다. 이는 대규모 문서 분석, 코드베이스 처리, 장편 콘텐츠 생성 등의 용도에서 게임 체인저가 될 것으로 예상된다."""
    
    resp = client.chat.completions.create(
        model="gpt-4o-mini",  # 비용 효율적인 모델 사용
        messages=[
            {"role": "system", "content": "You are an expert tech news analyst. Create detailed, insightful summaries that provide context and implications beyond the basic facts."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=300,  # 상세 요약이므로 토큰 수 증가
    )
    detailed_content = resp.choices[0].message.content or brief_summary
    
    return DetailedSummary(
        title=title,
        url=url,
        brief_summary=brief_summary,
        detailed_summary=detailed_content.strip()
    )


def summarize_with_details(openai_api_key: str, title: str, url: str, text: str, language: str = "ko") -> DetailedSummary:
    """한줄 요약과 상세 요약을 동시에 생성"""
    client = OpenAI(api_key=openai_api_key)
    
    # 통합 프롬프트 (한 번의 API 호출로 둘 다 생성)
    prompt = f"""다음 기술 뉴스를 한국어로 두 가지 방식으로 요약해주세요.

제목: {title}
URL: {url}

본문:
{text[:8000]}

요구사항:
1. 한줄요약: 50-100자, 핵심만 간결하게, "~했다"로 종료
2. 상세요약: 200-400자, 2-4문장, 배경-핵심-의미 포함

응답 형식:
한줄요약: [여기에 한줄 요약]
상세요약: [여기에 상세 요약]

예시:
한줄요약: OpenAI가 GPT-4 Turbo를 출시하며 128K 컨텍스트와 30% 저렴한 가격을 발표했다.
상세요약: OpenAI가 개발자 컨퍼런스에서 GPT-4 Turbo를 공식 발표했다. 새 모델은 기존 8K에서 128K 토큰으로 16배 확장된 컨텍스트 윈도우를 지원하며 300페이지 분량 문서를 한 번에 처리할 수 있다. 가격은 기존 GPT-4 대비 입력 3배, 출력 2배 저렴해져 API 비용을 대폭 절감한다. 대규모 문서 분석과 장편 콘텐츠 생성에서 게임 체인저가 될 전망이다."""
    
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a tech news summarizer who creates both brief and detailed summaries in Korean."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=400,
    )
    
    response_content = resp.choices[0].message.content or ""
    
    # 응답에서 한줄요약과 상세요약 분리
    brief_summary = ""
    detailed_summary = ""
    
    lines = response_content.split('\n')
    for line in lines:
        if line.startswith('한줄요약:'):
            brief_summary = line.replace('한줄요약:', '').strip()
        elif line.startswith('상세요약:'):
            detailed_summary = line.replace('상세요약:', '').strip()
    
    # 파싱 실패시 폴백
    if not brief_summary:
        brief_summary = response_content[:100] + "..." if len(response_content) > 100 else response_content
    if not detailed_summary:
        detailed_summary = response_content
    
    return DetailedSummary(
        title=title,
        url=url,
        brief_summary=brief_summary,
        detailed_summary=detailed_summary
    )