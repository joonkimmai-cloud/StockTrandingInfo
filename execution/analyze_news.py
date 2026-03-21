import os
import sys
import json
import asyncio
import aiohttp
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Windows 콘솔에서 utf-8 출력 강제 설정 (이모지/한글 깨짐 방지)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

KST = ZoneInfo('Asia/Seoul')

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
    1. 각 주식별로 거래량이 왜 급증했는지 전문적인 경제, 사회, 문화, 정치적 관점에서 분석을 덧붙여 주세요.
    2. 시장 전반의 테마(예: AI, 에너지, 환율, 전쟁 영향, 금리, 국제 정세 등)를 파악해 주세요.
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
        raise Exception(f"AI Analysis failed: {e}")

async def check_existing_analysis():
    # 오늘 자 분석 결과가 이미 DB에 있는지 확인합니다.
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key: return None
    
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
    today = datetime.now(KST).strftime('%Y-%m-%d')
    url = f"{supabase_url}/rest/v1/market_reports?report_date=eq.{today}&select=*"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if len(data) > 0:
                        report_id = data[0]['id']
                        # 리포트가 발견되면, 연결된 종목 분석도 가져옴
                        sa_url = f"{supabase_url}/rest/v1/stock_analysis?report_id=eq.{report_id}&select=*,companies(name)"
                        async with session.get(sa_url, headers=headers) as sa_resp:
                            if sa_resp.status == 200:
                                sa_data = await sa_resp.json()
                                # 재구성하여 리턴
                                result = {
                                    "status": "success",
                                    "is_cached": True, # 저장 스크립트에서 중복 저장을 방지하기 위한 플래그
                                    "market_summary": data[0].get('market_summary', ''),
                                    "prediction": data[0].get('prediction', ''),
                                    "kr_analysis": [],
                                    "us_analysis": []
                                }
                                for item in sa_data:
                                    # 원본 데이터를 정확히 복원하긴 어렵지만, 이메일용으로 표시될 내용은 복원 가능
                                    comp_name = item.get('companies', {}).get('name', '알수없음')
                                    analysis_obj = {
                                        "name": comp_name,
                                        "analysis": item.get('analysis_content', ''),
                                        "sentiment": item.get('sentiment', 'Neutral')
                                    }
                                    # 여기서는 모두 kr_analysis 에 넣음 (구분이 모호하더라도 이메일 발송엔 문제 없음)
                                    result["kr_analysis"].append(analysis_obj)
                                    
                                return result
    except Exception as e:
        print(f"Failed to check existing analysis: {e}")
    return None

async def main():
    # 패스 로직: DB에 이미 오늘자 분석이 완성되어 있으면 API 호출 전면 취소
    existing_report = await check_existing_analysis()
    if existing_report and existing_report.get('is_cached'):
        print("[3단계] 💡 DB에 오늘 자 AI 분석 데이터가 이미 존재합니다. (Gemini API 호출을 생략합니다)")
        with open('.tmp/report.json', 'w', encoding='utf-8') as f:
            json.dump(existing_report, f, ensure_ascii=False, indent=2)
        print("Report analysis (cached from DB) saved to .tmp/report.json")
        return

    if not os.path.exists('.tmp/news_data.json'):
        print("News data not found. Run get_news.py first.")
        sys.exit(1)

    with open('.tmp/news_data.json', 'r', encoding='utf-8') as f:
        news_data = json.load(f)

    print("Generating AI Analysis report...")
    try:
        final_report = await generate_analysis(news_data)
        print("[3단계] AI 분석 리포트 생성 종료")
    except Exception as e:
        print(f"===========================================================")
        print(f"[WARN] AI API error occurred! Falling back to raw headlines.")
        print(f"Error detail: {e}")
        print(f"===========================================================")
        
        # fallback for DB & Email
        fallback_kr = []
        for stock in news_data.get('kr', []):
            news_text = "\n".join([f"• {n.get('title', '')}" for n in stock.get('news', [])])
            if "**" in news_text: news_text = "- 수집된 관련 기사 및 공시 없음"
            fallback_kr.append({
                "name": stock.get('name'),
                "analysis": f"[AI 텍스트 분석 지연 - 수집된 헤드라인]\n{news_text}",
                "sentiment": "Neutral"
            })
            
        fallback_us = []
        for stock in news_data.get('us', []):
            news_text = "\n".join([f"• {n.get('title', '')}" for n in stock.get('news', [])])
            if "**" in news_text: news_text = "- 수집된 관련 기사 및 공시 없음"
            fallback_us.append({
                "name": stock.get('name'),
                "analysis": f"[AI 텍스트 분석 지연 - 수집된 헤드라인]\n{news_text}",
                "sentiment": "Neutral"
            })

        final_report = {
            "status": "success",
            "market_summary": f"⚠️ AI 분석 지연 (API 응답 실패). AI 시스템 에러로 부득이하게 로우 데이터(단순 기사 제목)를 전송합니다.\n사유: {str(e)}",
            "prediction": "가장 많이 검색된 주식들의 헤드라인을 직접 참조하여 주시기 바랍니다.",
            "kr_analysis": fallback_kr,
            "us_analysis": fallback_us,
            "raw_data": news_data
        }
    
    with open('.tmp/report.json', 'w', encoding='utf-8') as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    
    print("Report analysis saved to .tmp/report.json")

if __name__ == "__main__":
    asyncio.run(main())
