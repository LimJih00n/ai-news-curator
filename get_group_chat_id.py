#!/usr/bin/env python3
"""
텔레그램 그룹 Chat ID 확인 도구
"""
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

def get_chat_id(bot_token):
    """봇이 추가된 모든 채팅의 Chat ID 조회"""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if not data.get('ok'):
            print("❌ API 호출 실패:", data)
            return
            
        updates = data.get('result', [])
        
        if not updates:
            print("📝 메시지가 없습니다. 그룹에서 봇에게 메시지를 보내세요.")
            print("   예: /start 또는 아무 메시지")
            return
            
        print("🔍 발견된 채팅 목록:\n")
        
        seen_chats = set()
        for update in updates:
            message = update.get('message', {})
            chat = message.get('chat', {})
            
            chat_id = chat.get('id')
            chat_type = chat.get('type')
            chat_title = chat.get('title', 'N/A')
            chat_username = chat.get('username', 'N/A')
            
            if chat_id and chat_id not in seen_chats:
                seen_chats.add(chat_id)
                
                if chat_type == 'private':
                    print(f"👤 개인 채팅")
                    print(f"   Chat ID: {chat_id}")
                    print(f"   사용자: {chat.get('first_name', '')} {chat.get('last_name', '')}")
                elif chat_type == 'group':
                    print(f"👥 그룹 채팅")
                    print(f"   Chat ID: {chat_id}")
                    print(f"   그룹명: {chat_title}")
                elif chat_type == 'supergroup':
                    print(f"🏢 슈퍼그룹")
                    print(f"   Chat ID: {chat_id}")
                    print(f"   그룹명: {chat_title}")
                    print(f"   Username: @{chat_username}")
                elif chat_type == 'channel':
                    print(f"📢 채널")
                    print(f"   Chat ID: {chat_id}")
                    print(f"   채널명: {chat_title}")
                    print(f"   Username: @{chat_username}")
                
                print()
        
        print("💡 사용법:")
        print("1. 원하는 그룹의 Chat ID를 복사")
        print("2. .env 파일의 TELEGRAM_CHAT_ID를 해당 ID로 변경")
        print("3. 그룹에서는 보통 음수 Chat ID가 사용됩니다 (예: -1001234567890)")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def test_send_message(bot_token, chat_id):
    """특정 Chat ID로 테스트 메시지 전송"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        'chat_id': chat_id,
        'text': '🤖 AI 뉴스 큐레이터 봇 테스트 메시지입니다!\n\n이 메시지가 보이면 설정이 완료되었습니다.',
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, data=data)
        result = response.json()
        
        if result.get('ok'):
            print(f"✅ 테스트 메시지 전송 성공! (Chat ID: {chat_id})")
        else:
            print(f"❌ 메시지 전송 실패: {result}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN이 .env 파일에 설정되어 있지 않습니다.")
        exit(1)
    
    print("🤖 텔레그램 그룹 Chat ID 확인 도구")
    print("=" * 50)
    
    get_chat_id(bot_token)
    
    # 테스트 메시지 전송 (선택사항)
    print("\n" + "=" * 50)
    chat_id_input = input("테스트 메시지를 보낼 Chat ID를 입력하세요 (Enter 키로 건너뛰기): ").strip()
    
    if chat_id_input:
        try:
            chat_id = int(chat_id_input)
            test_send_message(bot_token, chat_id)
        except ValueError:
            print("❌ 유효하지 않은 Chat ID입니다.")