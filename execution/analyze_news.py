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
    수집된 뉴스 데이터를 기반으로 AI 분석 리포트를 생성합니다.
    """
    print("[5단계] AI 분석 리포트 생성 시작...")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY가 설정되지 않았습니다.")
        return None
        
    model_name = await get_valid_gemini_model(session, api_key)
    print(f"  * 사용 모델: [{model_name}]")

    prompt = f"""
    당신은 세계적인 시니어 투자 전략가이자 경제학자입니다. 
    최근 거래량 급증 종목에 대해 전문 분석 리포트를 작성해 주세요.
    
    [데이터]
    {json.dumps(news_data, ensure_ascii=False, indent=2)}
    
    [분석 가이드]
    1. 각 종목의 거래량 급증 원인을 제공된 다수의 뉴스(최대 10개)를 종합하여 다각도로 분석해 주세요 (매크로, 뉴스, 산업 테마).
    2. 시장 전반의 요약과 향후 증시 예측 (에널리스트 톤).
    3. Sentiment (Bullish/Bearish) 명시.
    4. 결과를 반드시 아래 JSON 구조로 출력하세요.
    
    [JSON 구조]
    {{
        "market_summary": "...",
        "kr_analysis": [ {{ "name": "...", "analysis": "...", "sentiment": "Bullish/Bearish" }} ],
        "us_analysis": [ {{ "name": "...", "analysis": "...", "sentiment": "Bullish/Bearish" }} ],
        "prediction": "..."
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
                print(f"Gemini API 오류: {response.status}")
                return None
            data = await response.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            return json.loads(text)
    except Exception as e:
        print(f"AI 분석 중 오류 발생: {e}")
        return None

async def main():
    check_lock()
    try:
        print("[5단계] AI 분석 시작...")
        if not os.path.exists('.tmp/news_data.json'):
            print("⚠️ 뉴스 데이터 파일이 없습니다. 3단계를 먼저 실행해 주세요.")
            return

        with open('.tmp/news_data.json', 'r', encoding='utf-8') as f:
            news_data = json.load(f)

        async with aiohttp.ClientSession() as session:
            report = await generate_analysis(session, news_data)
            
            if not report:
                print("❌ 오류: AI 분석 리포트 생성을 실패했습니다. (Gemini API 응답 없음)")
                sys.exit(1)

            with open('.tmp/report.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        print("[5단계] AI 분석 완료 (.tmp/report.json)")
    except Exception as e:
        print(f"대장 함수 실행 중 오류 발생: {e}")
    finally:
        remove_lock()

if __name__ == "__main__":
    asyncio.run(main())
