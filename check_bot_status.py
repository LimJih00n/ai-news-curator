#!/usr/bin/env python3
"""
텔레그램 봇 상태 및 그룹 멤버십 확인 도구
"""
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

def check_bot_info(bot_token):
    """봇 기본 정보 확인"""
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('ok'):
            bot_info = data['result']
            print("🤖 봇 정보:")
            print(f"   이름: {bot_info.get('first_name')}")
            print(f"   사용자명: @{bot_info.get('username')}")
            print(f"   ID: {bot_info.get('id')}")
            print(f"   그룹 지원: {'✅' if bot_info.get('can_join_groups') else '❌'}")
            print(f"   프라이버시 모드: {'✅' if bot_info.get('can_read_all_group_messages') else '❌'}")
            return True
        else:
            print("❌ 봇 토큰이 유효하지 않습니다:", data)
            return False
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def check_chat_member(bot_token, chat_id, user_id):
    """특정 채팅에서 봇의 멤버 상태 확인"""
    url = f"https://api.telegram.org/bot{bot_token}/getChatMember"
    
    params = {
        'chat_id': chat_id,
        'user_id': user_id
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('ok'):
            member_info = data['result']
            status = member_info.get('status')
            user = member_info.get('user', {})
            
            print(f"👤 멤버 상태:")
            print(f"   사용자: {user.get('first_name')} (@{user.get('username')})")
            print(f"   상태: {status}")
            
            status_description = {
                'creator': '👑 그룹 생성자',
                'administrator': '👨‍💼 관리자',  
                'member': '👤 일반 멤버',
                'restricted': '🚫 제한됨',
                'left': '👋 그룹을 떠남',
                'kicked': '❌ 추방됨'
            }
            
            print(f"   의미: {status_description.get(status, '알 수 없음')}")
            
            if status in ['member', 'administrator', 'creator']:
                print("✅ 봇이 그룹에 정상적으로 있습니다.")
                return True
            else:
                print("❌ 봇이 그룹에 없거나 문제가 있습니다.")
                return False
                
        else:
            error = data.get('description', '알 수 없는 오류')
            print(f"❌ 멤버 상태 확인 실패: {error}")
            
            # 일반적인 오류 해석
            if 'chat not found' in error.lower():
                print("💡 해결방법: Chat ID가 잘못되었거나 봇이 해당 채팅에 없습니다.")
            elif 'user not found' in error.lower():
                print("💡 해결방법: 봇 ID가 잘못되었습니다.")
            elif 'forbidden' in error.lower():
                print("💡 해결방법: 봇에게 권한이 없습니다. 그룹에 봇을 다시 초대해보세요.")
                
            return False
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def get_chat_info(bot_token, chat_id):
    """채팅 정보 확인"""
    url = f"https://api.telegram.org/bot{bot_token}/getChat"
    
    params = {'chat_id': chat_id}
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('ok'):
            chat_info = data['result']
            print(f"💬 채팅 정보:")
            print(f"   ID: {chat_info.get('id')}")
            print(f"   타입: {chat_info.get('type')}")
            print(f"   제목: {chat_info.get('title', 'N/A')}")
            print(f"   멤버 수: {chat_info.get('member_count', 'N/A')}")
            return True
        else:
            print(f"❌ 채팅 정보 확인 실패: {data.get('description')}")
            return False
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def send_test_message(bot_token, chat_id):
    """테스트 메시지 전송"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        'chat_id': chat_id,
        'text': '🤖 봇 상태 확인 테스트\n\n이 메시지가 보이면 봇이 정상 작동하고 있습니다!',
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, data=data)
        result = response.json()
        
        if result.get('ok'):
            print("✅ 테스트 메시지 전송 성공!")
            return True
        else:
            error = result.get('description', '알 수 없는 오류')
            print(f"❌ 테스트 메시지 전송 실패: {error}")
            
            # 오류 해석
            if 'chat not found' in error.lower():
                print("💡 해결방법: Chat ID가 잘못되었습니다.")
            elif 'forbidden' in error.lower():
                print("💡 해결방법: 봇이 그룹에서 메시지 전송 권한이 없습니다.")
            elif 'bot was blocked' in error.lower():
                print("💡 해결방법: 사용자가 봇을 차단했습니다.")
                
            return False
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

if __name__ == "__main__":
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN이 .env 파일에 설정되어 있지 않습니다.")
        exit(1)
    
    print("🔍 텔레그램 봇 상태 확인 도구")
    print("=" * 50)
    
    # 1. 봇 정보 확인
    print("1️⃣ 봇 정보 확인")
    bot_valid = check_bot_info(bot_token)
    print()
    
    if not bot_valid:
        exit(1)
    
    # 2. 채팅 ID 입력 받기
    if not chat_id:
        chat_id = input("확인할 Chat ID를 입력하세요: ").strip()
    
    if not chat_id:
        print("❌ Chat ID가 필요합니다.")
        exit(1)
    
    try:
        chat_id = int(chat_id)
    except ValueError:
        print("❌ 유효하지 않은 Chat ID입니다.")
        exit(1)
    
    print(f"2️⃣ 채팅 정보 확인 (Chat ID: {chat_id})")
    get_chat_info(bot_token, chat_id)
    print()
    
    # 3. 봇 ID 가져오기
    bot_info_url = f"https://api.telegram.org/bot{bot_token}/getMe"
    try:
        response = requests.get(bot_info_url)
        bot_data = response.json()
        bot_id = bot_data['result']['id']
        
        print(f"3️⃣ 봇 멤버십 상태 확인 (Bot ID: {bot_id})")
        check_chat_member(bot_token, chat_id, bot_id)
        print()
        
    except Exception as e:
        print(f"❌ 봇 ID 확인 실패: {e}")
        exit(1)
    
    # 4. 테스트 메시지 전송
    print("4️⃣ 테스트 메시지 전송")
    test_confirm = input("테스트 메시지를 전송하시겠습니까? (y/N): ").lower().strip()
    
    if test_confirm == 'y':
        send_test_message(bot_token, chat_id)
    
    print("\n" + "=" * 50)
    print("✅ 봇 상태 확인 완료!")