import os
import sys
import json
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def get_valid_gemini_model(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get('models', [])
                    
                    # 1. 'flash' 모델 우선 검색
                    for m in models:
                        if 'flash' in m.get('name', '').lower() and 'generateContent' in m.get('supportedGenerationMethods', []):
                            return m['name']
                            
                    # 2. 'pro' 모델 차선책
                    for m in models:
                        if 'pro' in m.get('name', '').lower() and 'generateContent' in m.get('supportedGenerationMethods', []):
                            return m['name']
    except Exception as e:
        print(f"Model auto-discovery failed: {e}")
        
    return "models/gemini-1.5-flash" # 최후의 하드코딩 Fallback

async def generate_analysis(stock_data):
    print("[3단계] AI 분석 리포트 생성 시작...")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY is not set.")
        sys.exit(1)
        
    model_name = await get_valid_gemini_model(api_key)
    print(f"  * Auto-Discovery 통과: [{model_name}] 모델을 사용하여 분석을 시도합니다.")

    prompt = f"""
    당신은 세계적인 시니어 투자 전략가이자 경제학자입니다. 
    최근 전날 대비 거래량이 급증한(Relative Volume) 한국 및 미국 주식 정보를 바탕으로 리포트를 작성해 주세요.
    
    [데이터 정보]
    {json.dumps(stock_data, ensure_ascii=False, indent=2)}
    
    [요청 사항]
    1. 각 주식별로 거래량이 왜 급증했는지(뉴스 기반) 전문적인 경제 분석을 덧붙여 주세요.
    2. 시장 전반의 테마(예: AI, 에너지, 환율 영향)를 파악해 주세요.
    3. 경제학적 개념을 사용하여 오늘의 증시를 예측해 주세요.
    4. 분석은 한국어로 작성하며, 에널리스트 톤을 유지하세요.
    
    [출력 형식]
    반드시 아래와 같은 JSON 구조로 응답하세요:
    {{
        "market_summary": "전체 시장 요약",
        "kr_analysis": [
            {{ "name": "종목명", "analysis": "분석내용", "sentiment": "Bullish/Bearish" }}
        ],
        "us_analysis": [
            {{ "name": "종목명", "analysis": "분석내용", "sentiment": "Bullish/Bearish" }}
        ],
        "prediction": "오늘의 증시 예측 및 투자 전략"
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json"
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API Error {response.status}: {error_text}")
                    
                data = await response.json()
                
                candidates = data.get('candidates', [])
                if not candidates:
                    raise Exception(f"No candidates returned: {data}")
                    
                content = candidates[0].get('content')
                if not content:
                    finish_reason = candidates[0].get('finishReason', 'Unknown')
                    raise Exception(f"Model blocked or empty content. Finish Reason: {finish_reason}, Data: {data}")
                    
                parts = content.get('parts', [])
                if not parts:
                    raise Exception(f"Model returned no text parts. Data: {data}")
                    
                text = parts[0].get('text', '').strip()
                
                # 안전하게 JSON 블록(```json ... ```)만 추출하기 (머리말/꼬리말 무시)
                import re
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
                if match:
                    text = match.group(1).strip()
                else:
                    # 혹시 ```가 아예 없이 { 로 시작할 수도 있으니 첫 번째 '{' 와 마지막 '}' 사이만 남기기
                    start_idx = text.find('{')
                    end_idx = text.rfind('}')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        text = text[start_idx:end_idx+1]
                
                try:
                    result = json.loads(text)
                except Exception as je:
                    print(f"--- 🚨 JSON Parsing Failed ---")
                    print(f"Raw Model Output (first 1000 chars):\n{text[:1000]}")
                    print(f"------------------------------")
                    raise Exception(f"Failed to parse model output as JSON. Error: {je}")
                
                result['status'] = 'success'
                return result
    except Exception as e:
        print(f"AI Analysis failed: {e}")
        sys.exit(1)

async def main():
    if not os.path.exists('.tmp/news_data.json'):
        print("News data not found. Run get_news.py first.")
        sys.exit(1)

    with open('.tmp/news_data.json', 'r', encoding='utf-8') as f:
        news_data = json.load(f)

    print("Generating AI Analysis report...")
    final_report = await generate_analysis(news_data)
    print("[3단계] AI 분석 리포트 생성 종료")
    
    with open('.tmp/report.json', 'w', encoding='utf-8') as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    
    print("Report analysis saved to .tmp/report.json")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal Error during AI analysis: {e}")
        sys.exit(1)
