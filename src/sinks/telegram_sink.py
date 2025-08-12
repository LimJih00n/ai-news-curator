from __future__ import annotations

from typing import List, Union
import requests
from src.models import ContentItem, ArxivItem, YoutubeItem


class TelegramSink:
    def __init__(self, bot_token: str, chat_id: str):
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._api_url = f"https://api.telegram.org/bot{bot_token}"

    def _send_message(self, text: str) -> bool:
        """텔레그램 메시지 전송"""
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
            print(f"텔레그램 메시지 전송 실패: {e}")
            return False

    def send_digest(self, title: str, items: List[Union[ContentItem, ArxivItem, YoutubeItem]], max_items: int = 5) -> None:
        """뉴스 다이제스트를 텔레그램으로 전송 (간결한 형식)"""
        if not items:
            return
        
        # 상위 max_items개만 선별
        top_items = items[:max_items]
            
        # 헤더 메시지 (한 번만 전송)
        header = f"🤖 *{title}*\n\n📊 오늘의 주요 AI/IT 뉴스 TOP {len(top_items)}\n\n"
        
        # 모든 아이템을 하나의 메시지로 구성
        message_lines = [header]
        
        for i, item in enumerate(top_items, 1):
            # 중요도 평가 (getattr로 안전하게 접근)
            importance_score = getattr(item, 'importance_score', 3.0)
            stars = self._get_importance_stars(importance_score)
            
            # 한글 제목 생성 (요약이 한글이므로 요약에서 핵심 키워드 추출)
            korean_title = self._extract_korean_title(item)
            
            # 간결한 한 줄 형식: 별점 + 한글제목 + 링크
            line = f"{stars} {korean_title} [🔗]({item.link})"
            message_lines.append(line)
        
        # 푸터 추가
        footer = f"\n📋 총 {len(top_items)}개 선별 | 🕐 {title.split(' - ')[-1] if ' - ' in title else '오늘'}"
        message_lines.append(footer)
        
        # 전체 메시지 구성 및 전송
        full_message = "\n".join(message_lines)
        
        # 메시지 길이 확인 (텔레그램 4096자 제한)
        if len(full_message) > 4000:
            # 길면 아이템 수 줄이기
            return self.send_digest(title, items, max_items - 1)
            
        success = self._send_message(full_message)
        if success:
            print(f"✅ 텔레그램 간결 형식 전송 완료: {len(top_items)}개 아이템")
        else:
            print(f"❌ 텔레그램 전송 실패")
    
    def _get_importance_stars(self, score: float) -> str:
        """중요도 점수를 별점으로 변환"""
        if score >= 4.5:
            return "⭐⭐⭐⭐⭐"
        elif score >= 3.5:
            return "⭐⭐⭐⭐"
        elif score >= 2.5:
            return "⭐⭐⭐"
        elif score >= 1.5:
            return "⭐⭐"
        else:
            return "⭐"
    
    def _extract_korean_title(self, item) -> str:
        """영어 제목을 한글로 변환하거나 요약에서 핵심 추출"""
        # 요약이 이미 한글이므로 요약의 핵심 부분을 제목으로 사용
        summary = getattr(item, 'summary', '')
        if summary:
            # 요약에서 첫 번째 문장의 핵심만 추출 (40자 제한)
            core = summary.split('다.')[0] + '다' if '다.' in summary else summary
            return core[:40] + "..." if len(core) > 40 else core
        else:
            # 요약이 없으면 원제목 사용 (30자 제한)
            original_title = getattr(item, 'title', '')
            return original_title[:30] + "..." if len(original_title) > 30 else original_title
