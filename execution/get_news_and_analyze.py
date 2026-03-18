import os
import json
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Gemini Setup
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

async def fetch_news_for_stock(session, stock):
    symbol = stock['symbol']
    name = stock['name']
    market = stock['market']
    
    # Simple Google News search URL
    query = f"{name} {symbol} stock news"
    url = f"https://www.google.com/search?q={query}&tbm=nws"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        async with session.get(url, headers=headers) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            articles = []
            # This selector is a common patterns but search results change often
            # We'll take the first 4 results that look like news items
            news_items = soup.select('div.So0oBc, div.BNeawe.vvv07z.AP7Wnd') # Basic fallback selectors
            
            for item in news_items[:4]:
                title = item.get_text()
                if title:
                    articles.append(title)
            
            return {
                **stock,
                'news': articles if articles else ["No recent news found for this target volume surge."]
            }
    except Exception as e:
        print(f"Error scraping news for {symbol}: {e}")
        return {**stock, 'news': ["Error fetching news."]}

async def generate_analysis(stock_data):
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
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith('```json'):
            text = text[7:-3].strip()
        elif text.startswith('```'):
            text = text[3:-3].strip()
        
        result = json.loads(text)
        result['status'] = 'success'
        return result
    except Exception as e:
        print(f"AI Analysis failed: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "market_summary": "AI 분석 세션에 오류가 발생했습니다.",
            "raw_data": stock_data, # 기사 정보를 보존
            "prediction": "AI 분석 실패로 인해 예측을 제공할 수 없습니다."
        }


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
    
    print("Generating AI Analysis report...")
    final_report = await generate_analysis(analysis_input)
    
    with open('.tmp/report.json', 'w', encoding='utf-8') as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    
    print("Report analysis saved to .tmp/report.json")

if __name__ == "__main__":
    asyncio.run(main())
