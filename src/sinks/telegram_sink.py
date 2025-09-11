from __future__ import annotations

from typing import List, Union, Optional
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

    def send_digest(self, title: str, items: List[Union[ContentItem, ArxivItem, YoutubeItem]], max_items: int = 5, notion_url: str = None) -> None:
        """뉴스 다이제스트를 텔레그램으로 전송 (개선된 형식)"""
        if not items:
            return
        
        # 상위 max_items개만 선별
        top_items = items[:max_items]
            
        # 헤더 메시지 (이모지와 함께)
        header = f"🚀 *{title}*\n"
        header += f"━━━━━━━━━━━━━━━━━━━━\n"
        header += f"📅 {title.split(' - ')[-1] if ' - ' in title else '오늘'} | 🔥 TOP {len(top_items)} 큐레이션\n\n"
        
        # 모든 아이템을 하나의 메시지로 구성
        message_lines = [header]
        
        for i, item in enumerate(top_items, 1):
            # 중요도 평가 (getattr로 안전하게 접근)
            importance_score = getattr(item, 'importance_score', 3.0)
            
            # 중요도에 따른 이모지 선택
            importance_emoji = self._get_importance_emoji(importance_score)
            
            # 한글 제목 생성
            korean_title = self._extract_korean_title(item)
            
            # 소스 정보 (짧게)
            source = self._get_short_source(item)
            
            # 개선된 형식: 순위 + 이모지 + 제목 + 소스 + 링크
            line = f"*{i}.* {importance_emoji} {korean_title}\n"
            line += f"   └ {source} [자세히 보기]({item.link})\n"
            message_lines.append(line)
        
        # 푸터에 노션 링크 추가
        footer_parts = [f"\n📋 총 {len(top_items)}개 선별"]
        
        if notion_url:
            footer_parts.append(f"📚 [상세 보기 (Notion)]({notion_url})")
            
        footer_parts.append(f"🕐 {title.split(' - ')[-1] if ' - ' in title else '오늘'}")
        footer = " | ".join(footer_parts)
        message_lines.append(footer)
        
        # 전체 메시지 구성 및 전송
        full_message = "\n".join(message_lines)
        
        # 메시지 길이 확인 (텔레그램 4096자 제한)
        if len(full_message) > 4000:
            # 길면 아이템 수 줄이기
            return self.send_digest(title, items, max_items - 1, notion_url)
            
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
    
    def _get_importance_emoji(self, score: float) -> str:
        """중요도 점수를 이모지로 변환 (더 시각적)"""
        if score >= 4.5:
            return "🔥"  # 핫 이슈
        elif score >= 3.5:
            return "⚡"  # 중요
        elif score >= 2.5:
            return "💡"  # 주목
        elif score >= 1.5:
            return "📌"  # 일반
        else:
            return "📄"  # 참고
    
    def _get_short_source(self, item) -> str:
        """소스를 짧게 표시"""
        source = getattr(item, 'source', 'Unknown')
        
        # URL에서 도메인 추출
        if 'http' in source:
            from urllib.parse import urlparse
            domain = urlparse(source).netloc
            domain = domain.replace('www.', '').replace('.com', '').replace('.org', '')
            return domain[:15]
        
        # 긴 소스명 축약
        source_map = {
            'Hacker News': 'HN',
            'TechCrunch': 'TC',
            'The Verge': 'Verge',
            'MIT Technology Review': 'MIT Tech',
            'Google AI Blog': 'Google AI',
            'OpenAI Blog': 'OpenAI',
            'Hugging Face Blog': 'HF',
            'arxiv.org': 'arXiv',
            'YouTube': 'YT',
        }
        
        for full, short in source_map.items():
            if full in source:
                return short
        
        return source[:10]
    
    def _extract_korean_title(self, item) -> str:
        """영어 제목을 한글로 변환하거나 요약에서 핵심 추출 (짧게)"""
        # 요약이 이미 한글이므로 요약의 핵심 부분을 제목으로 사용
        summary = getattr(item, 'summary', '')
        if summary:
            # 요약에서 첫 번째 문장의 핵심만 추출 (25자 제한으로 더 짧게)
            core = summary.split('다.')[0] + '다' if '다.' in summary else summary
            # 불필요한 단어 제거
            core = core.replace('발표했다', '발표').replace('출시했다', '출시').replace('도입했다', '도입')
            return core[:25] + "..." if len(core) > 25 else core
        else:
            # 요약이 없으면 원제목 사용 (20자 제한)
            original_title = getattr(item, 'title', '')
            return original_title[:20] + "..." if len(original_title) > 20 else original_title
    
    def send_digest_separated(self, 
                             title: str, 
                             news_items: List, 
                             paper_items: List,
                             notion_url: Optional[str] = None) -> None:
        """뉴스와 논문을 구분하여 전송"""
        if not news_items and not paper_items:
            return
        
        # 헤더 메시지
        header = f"🚀 *{title}*\n"
        header += f"━━━━━━━━━━━━━━━━━━━━\n"
        header += f"📅 {title.split(' - ')[-1] if ' - ' in title else '오늘'}\n\n"
        
        message_lines = [header]
        
        # 뉴스 섹션
        if news_items:
            message_lines.append("📰 *AI/Tech News TOP 5*\n")
            for i, item in enumerate(news_items[:5], 1):
                importance_score = getattr(item, 'importance_score', 3.0)
                importance_emoji = self._get_importance_emoji(importance_score)
                korean_title = self._extract_korean_title(item)
                source = self._get_short_source(item)
                
                line = f"*{i}.* {importance_emoji} {korean_title}\n"
                line += f"   └ {source} [링크]({item.link})\n"
                message_lines.append(line)
        
        # 구분선
        if news_items and paper_items:
            message_lines.append("\n───────────────\n\n")
        
        # 논문 섹션
        if paper_items:
            message_lines.append("📚 *Research Papers TOP 3*\n")
            for i, paper in enumerate(paper_items[:3], 1):
                # 논문은 평가 정보 활용
                score = getattr(paper, 'importance_score', 5.0)
                evaluation = getattr(paper, 'evaluation', None)
                
                # 논문 제목 (짧게)
                paper_title = paper.title[:40] + "..." if len(paper.title) > 40 else paper.title
                
                # 카테고리
                categories = getattr(paper, 'categories', [])
                cat_str = ', '.join(categories[:2]) if categories else 'AI/ML'
                
                # 추천 이유
                if evaluation and hasattr(evaluation, 'recommendation'):
                    reason = evaluation.recommendation[:30] + "..."
                else:
                    reason = "주목할 연구"
                
                line = f"*{i}.* 📄 [{cat_str}] {paper_title}\n"
                line += f"   └ {reason} [arXiv]({paper.link})\n"
                message_lines.append(line)
        
        # 푸터
        footer = f"\n━━━━━━━━━━━━━━━━━━━━\n"
        footer += f"📊 뉴스 {len(news_items)}개 | 논문 {len(paper_items)}개\n"
        if notion_url:
            footer += f"📚 [Notion에서 전체 보기]({notion_url})"
        
        message_lines.append(footer)
        
        # 전체 메시지 전송
        full_message = "\n".join(message_lines)
        
        # 메시지 길이 체크
        if len(full_message) > 4000:
            # 너무 길면 항목 줄이기
            if len(news_items) > 3:
                return self.send_digest_separated(title, news_items[:3], paper_items[:2], notion_url)
        
        success = self._send_message(full_message)
        if success:
            print(f"✅ 텔레그램 전송 완료: 뉴스 {len(news_items)}개 + 논문 {len(paper_items)}개")
        else:
            print(f"❌ 텔레그램 전송 실패")
