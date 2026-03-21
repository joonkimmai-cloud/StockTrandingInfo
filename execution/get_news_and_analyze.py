import os
import json
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
KST = ZoneInfo('Asia/Seoul')

load_dotenv()

async def fetch_news_for_stock(session, stock):
    # 주식 정보 추출
    symbol = stock['symbol']
    name = stock['name']
    
    # SerpApi 키 가져오기 (.env 파일에 저장된 값)
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        print(f"Error: SERPAPI_API_KEY is not set.")
        return {**stock, 'news': [{"title": "API Key Error", "url": "#", "source": "System", "snippet": "SERPAPI_API_KEY가 설정되지 않았습니다."}]}
        
    # 뉴스 검색어 설정 (종목명, 티커 등에 '공시', '실적' 등 키워드 조합 가능)
    query = f"{name} {symbol} 주식 뉴스"
    
    # SerpApi 요청 URL 및 파라미터 설정
    # engine=google: 구글 검색 엔진 사용
    # tbm=nws: 구글 '뉴스' 탭 검색을 의미함
    # num=4: 가져올 뉴스 기사 수 (최대 4개)
    params = {
        "engine": "google",
        "q": query,
        "tbm": "nws",
        "api_key": serpapi_key,
        "num": "4"
    }
    
    try:
        print(f"  [2단계] {name}({symbol}) 뉴스 수집 중 (SerpApi 사용)...")
        # SerpApi로 HTTP GET 요청 보내기
        async with session.get("https://serpapi.com/search", params=params) as response:
            data = await response.json()
            
            articles = []
            # 결과 중 'news_results' 리스트가 있는지 확인
            if 'news_results' in data:
                # 최대 4개의 뉴스 데이터를 가져와서 리스트에 추가
                for item in data['news_results'][:4]:
                    articles.append({
                        'title': item.get('title', '제목 없음'),
                        'url': item.get('link', '#'),
                        'source': item.get('source', 'Google News'),
                        'timestamp': item.get('date', datetime.now(KST).isoformat()),
                        'snippet': item.get('snippet', ''),          # 기사 요약
                        'thumbnail_url': item.get('thumbnail', '')   # 썸네일 이미지 주소
                    })
                    
            status = "success" if articles else "no_news_found"
            print(f"  [2단계] {name}({symbol}) 뉴스 기사 수집 완료. (조회 수: {len(articles)})")
            
            # 수집된 기사가 없으면 기본 안내 메시지 추가
            if not articles:
                articles = [{
                    "title": "** 관련 기사 및 공시 없음", 
                    "url": "#", 
                    "source": "N/A", 
                    "snippet": "", 
                    "thumbnail_url": ""
                }]
                
            return {
                **stock,
                'news': articles,
                'news_status': status,
                'period': 'SerpApi'
            }
    except Exception as e:
        # 에러 발생 시 처리 (예: 인터넷 연결 문제, API 오류 등)
        print(f"Error scraping news for {symbol}: {e}")
        return {**stock, 'news': [{"title": "뉴스 수집 중 오류 발생", "url": "#", "source": "Error", "snippet": str(e), "thumbnail_url": ""}]}

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
        raise Exception("GOOGLE_API_KEY is not set.")
        
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
            "temperature": 0.7
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
                    
                text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                text = text.strip()
                
                if text.startswith('```json'):
                    text = text[7:-3].strip()
                elif text.startswith('```'):
                    text = text[3:-3].strip()
                
                result = json.loads(text)
                result['status'] = 'success'
                return result
    except Exception as e:
        print(f"AI Analysis failed: {e}")
        # raise here so main can catch it and return code 1
        raise e

async def main():
    if not os.path.exists('.tmp/market_data.json'):
        print("Market data not found. Run get_stock_data.py first.")
        return

    with open('.tmp/market_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("Scraping news for tickers...")
    async with aiohttp.ClientSession() as session:
        # Fetch news for all stocks concurrently
        tasks = []
        for stock in data['kr'] + data['us']:
            tasks.append(fetch_news_for_stock(session, stock))
        
        results = await asyncio.gather(*tasks)
        
    kr_news = results[:len(data['kr'])]
    us_news = results[len(data['kr']):]
    
    analysis_input = {
        'timestamp': data['timestamp'],
        'kr': kr_news,
        'us': us_news
    }
    
    # Save the raw news data before analysis for DB syncing
    with open('.tmp/news_data.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_input, f, ensure_ascii=False, indent=2)
    print("Raw news data saved to .tmp/news_data.json")

    print("Generating AI Analysis report...")
    final_report = await generate_analysis(analysis_input)
    print("[3단계] AI 분석 리포트 생성 종료")
    with open('.tmp/report.json', 'w', encoding='utf-8') as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    
    print("Report analysis saved to .tmp/report.json")

async def main_wrapped():
    try:
        await main()
    except Exception as e:
        print(f"Fatal Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import sys
    asyncio.run(main_wrapped())
