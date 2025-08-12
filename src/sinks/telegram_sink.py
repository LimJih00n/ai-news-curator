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

    def send_digest(self, title: str, items: List[Union[ContentItem, ArxivItem, YoutubeItem]]) -> None:
        """뉴스 다이제스트를 텔레그램으로 전송"""
        if not items:
            return
            
        # 헤더 메시지
        header = f"🤖 *{title}*\n\n📊 오늘의 주요 AI/IT 뉴스 (상위 {len(items)}개)\n\n"
        
        # 각 뉴스 아이템을 개별 메시지로 전송
        for i, item in enumerate(items, 1):
            # 소스명 추출
            source = getattr(item, 'source', 'Unknown')
            if 'https://' in source:
                source_name = source.replace('https://', '').replace('http://', '').split('/')[0]
            else:
                source_name = source
                
            # 메시지 구성
            message = f"{header if i == 1 else ''}"
            message += f"📰 *{i}. {source_name}*\n"
            message += f"**{item.title}**\n\n"
            message += f"{item.summary or ''}\n\n"
            message += f"🔗 [원문 보기]({item.link})"
            
            # 메시지 전송 (텔레그램 메시지 길이 제한: 4096자)
            if len(message) > 4000:
                # 요약 자르기
                summary_limit = 4000 - len(message) + len(item.summary or '')
                short_summary = (item.summary or '')[:summary_limit] + "..."
                message = f"{header if i == 1 else ''}"
                message += f"📰 *{i}. {source_name}*\n"
                message += f"**{item.title}**\n\n"
                message += f"{short_summary}\n\n"
                message += f"🔗 [원문 보기]({item.link})"
            
            success = self._send_message(message)
            if success:
                print(f"✅ 텔레그램 전송 완료: {item.title[:30]}...")
            else:
                print(f"❌ 텔레그램 전송 실패: {item.title[:30]}...")
                
        # 마지막 요약 메시지
        summary_msg = f"\n📋 총 {len(items)}개 뉴스를 전송했습니다.\n🕐 {title.split(' - ')[-1] if ' - ' in title else '오늘'}"
        self._send_message(summary_msg)
