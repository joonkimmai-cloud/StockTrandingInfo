import os
import sys
import json
import asyncio
import aiohttp
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

KST = ZoneInfo('Asia/Seoul')
load_dotenv()

# [기능] 다른 프로그램이 실행 중인지 확인하기 위한 락(Lock) 기능을 설정합니다.
LOCK_FILE = '.tmp/analyze_news.lock'

def check_lock():
    os.makedirs('.tmp', exist_ok=True)
    if os.path.exists(LOCK_FILE):
        file_time = os.path.getmtime(LOCK_FILE)
        if (datetime.now().timestamp() - file_time) < 3600:
            print("⚠️ AI 분석이 이미 진행 중입니다.")
            sys.exit(0)
    with open(LOCK_FILE, 'w', encoding='utf-8') as f:
        f.write(str(os.getpid()))

def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

def get_api_key_with_rotation():
    state_file = '.tmp/api_key_state.json'
    today = datetime.now(KST).strftime('%Y-%m-%d')
    state = {'current_index': 1, 'last_reset_date': today}
    
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                saved_state = json.load(f)
                if saved_state.get('last_reset_date') == today:
                    state = saved_state
        except Exception as e:
            print(f"Error reading api_state: {e}")

    key_env_var = f"GOOGLE_API_KEY_{state['current_index']}"
    api_key = os.getenv(key_env_var)
    if not api_key and state['current_index'] != 1:
        state['current_index'] = 1
        api_key = os.getenv("GOOGLE_API_KEY_1")
    return api_key, state

def save_api_key_state(state):
    state_file = '.tmp/api_key_state.json'
    os.makedirs('.tmp', exist_ok=True)
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def rotate_api_key(state):
    if state['current_index'] < 3:
        state['current_index'] += 1
        print(f"  --> Rotating to API Key #{state['current_index']}...")
        save_api_key_state(state)
        return True
    return False

async def get_valid_gemini_model(session, api_key):
    """사용 가능한 Gemini 모델을 자동으로 찾습니다."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                for m in data.get('models', []):
                    if 'flash' in m.get('name', '').lower() and 'generateContent' in m.get('supportedGenerationMethods', []):
                        return m['name']
    except: pass
    return "models/gemini-1.5-flash"

async def generate_analysis(session, news_data):
    """
    수집된 뉴스 데이터를 기반으로 AI 분석 리포트를 생성합니다. (API 로테이션 지원)
    """
    print("[5단계] AI 분석 리포트 생성 시작...")
    
    while True:
        api_key, state = get_api_key_with_rotation()
        if not api_key:
            print(f"GOOGLE_API_KEY_{state['current_index']} is not set.")
            if rotate_api_key(state): continue
            else: return None
            
        model_name = await get_valid_gemini_model(session, api_key)
        print(f"  * 사용 모델: [{model_name}] (Key #{state['current_index']})")

        prompt = f"""
        당신은 세계적인 시니어 투자 전략가이자 경제학자입니다. 
        최근 거래량 급증 종목에 대해 전문 분석 리포트를 작성해 주세요.
        
        [데이터]
        {json.dumps(news_data, ensure_ascii=False, indent=2)}
        
        [분석 가이드]
        1. 각 종목의 거래량 급증 원인을 제공된 다수의 뉴스(최대 10개)를 종합하여 다각도로 분석해 주세요 (경제, 사회, 문화, 기술, 국제).
        2. 시장 전반의 요약과 향후 증시 예측 (에널리스트 톤).
        3. Sentiment (Bullish/Bearish) 명시.
        4. 결과를 반드시 JSON 구조로만 출력하세요.
        5. 분석 대상 종목의 symbol을 데이터에서 찾아 반드시 포함해 주세요.
        
        [JSON 구조]
        {{
            "market_summary": "...",
            "investment_strategy": "...",
            "prediction": "...",
            "kr_analysis": [ {{ "name": "...", "symbol": "...", "analysis": "...", "sentiment": "Bullish/Bearish" }} ],
            "us_analysis": [ {{ "name": "...", "symbol": "...", "analysis": "...", "sentiment": "Bullish/Bearish" }} ]
        }}
        """
        
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.5, "responseMimeType": "application/json"}
        }
        
        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    print(f"Gemini API 오류 (Key #{state['current_index']}): {response.status}")
                    if response.status in [400, 429, 401]:
                        if rotate_api_key(state): continue
                    return None
                data = await response.json()
                text = data['candidates'][0]['content']['parts'][0]['text']
                save_api_key_state(state)
                return json.loads(text)
        except Exception as e:
            print(f"AI 분석 중 오류 발생 (Key #{state['current_index']}): {e}")
            if rotate_api_key(state): continue
            return None

async def check_existing_analysis(session):
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key: return None
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
    today = datetime.now(KST).strftime('%Y-%m-%d')
    url = f"{supabase_url}/rest/v1/market_reports?report_date=eq.{today}&select=*"
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                if len(data) > 0: return True
    except: pass
    return False

async def main():
    check_lock()
    try:
        print("[5단계] AI 분석 시작...")
        if not os.path.exists('.tmp/news_data.json'):
            print("❌ 오류: 뉴스 데이터 파일이 없습니다. (3단계 뉴스 수집 미완료)")
            sys.exit(1)

        with open('.tmp/news_data.json', 'r', encoding='utf-8') as f:
            news_data = json.load(f)

        async with aiohttp.ClientSession() as session:
            if await check_existing_analysis(session):
                print("[5단계] (INFO) DB에 오늘 자 AI 분석 리포트가 이미 존재하여 작업을 생략합니다.")
                return

            report = await generate_analysis(session, news_data)
            
            if not report:
                print("❌ 오류: AI 분석 리포트 생성을 실패했습니다. (Gemini API 응답 없음)")
                sys.exit(1)

            with open('.tmp/report.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        print("[5단계] AI 분석 완료 (.tmp/report.json)")
    except Exception as e:
        print(f"❌ 오류: 대장 함수 실행 중 오류 발생: {e}")
        sys.exit(1)
    finally:
        remove_lock()

if __name__ == "__main__":
    asyncio.run(main())
