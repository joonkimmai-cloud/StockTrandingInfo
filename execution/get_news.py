import os
import sys
import json
import asyncio
import aiohttp
from datetime import datetime
from aiohttp import BasicAuth
from zoneinfo import ZoneInfo

KST = ZoneInfo('Asia/Seoul')

from dotenv import load_dotenv

import trafilatura
from markdownify import markdownify as md

load_dotenv()

async def resolve_google_news_url(session, url):
    """Google News 리다이렉트 URL을 실제 기사 URL로 변환합니다."""
    if 'news.google.com' not in url:
        return url
    try:
        # allow_redirects=True로 실제 목적지 URL을 가져옴
        # 일부 뉴스 사이트는 HEAD 요청을 거부할 수 있으므로 GET을 사용
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        async with session.get(url, headers=headers, allow_redirects=True, timeout=10) as resp:
            target = str(resp.url)
            print(f"  [Info] Resolved Google News -> {target}")
            return target
    except Exception as e:
        print(f"  [Warning] URL resolution failed for {url}: {e}")
        return url

async def fetch_full_content(session, url):
    """기사 URL에서 본문 내용을 가져와 Markdown으로 변환합니다."""
    if not url or url == '#': 
        return ""
    
    # Google News 리다이렉트 해제
    target_url = await resolve_google_news_url(session, url)
    
    try:
        # 현실적인 브라우저 헤더 설정 (차단 방지)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/"
        }
        async with session.get(target_url, headers=headers, timeout=15) as response:
            if response.status == 200:
                html = await response.text()
                # trafilatura를 사용하여 본문 추출
                content = trafilatura.extract(html, output_format='markdown', include_links=True, include_images=False)
                if not content:
                    # trafilatura 실패 시 markdownify로 대체 시도
                    content = md(html, strip=['script', 'style', 'nav', 'header', 'footer'])
                return content if content else ""
            else:
                print(f"  [Error] HTTP {response.status} for {target_url}")
    except Exception as e:
        print(f"  [Error] Content fetch failed for {target_url}: {e}")
    return ""

async def check_existing_news(session, symbol, all_db_companies):
    today = datetime.now(KST).strftime('%Y-%m-%d')
    company = next((c for c in all_db_companies if c['symbol'] == symbol), None)
    if not company: return None
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key: return None
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    
    # 해당 회사의 오늘자 뉴스가 1개라도 있는지 확인
    url = f"{supabase_url}/rest/v1/news_articles?company_id=eq.{company['id']}&created_at=gte.{today}T00:00:00%2B09:00"
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                if len(data) > 0:
                    print(f"  [2단계] {symbol}: 💡 DB에 오늘자 뉴스가 이미 존재합니다. (API 호출 패스)")
                    # DB에 있는 뉴스 데이터를 그대로 반환 모양에 맞춰 재구성
                    articles = []
                    for item in data[:4]:
                        articles.append({
                            'title': item.get('title', ''),
                            'url': item.get('source_url', '#'),
                            'source': item.get('source_name', 'DB'),
                            'snippet': item.get('snippet', ''),
                            'content': item.get('content', ''),
                            'thumbnail_url': item.get('thumbnail_url', '')
                        })
                    return {"is_cached": True, "articles": articles}
    except Exception as e:
        print(f"Skipping DB check error for {symbol}: {e}")
    
    return None

async def fetch_news_for_stock(session, stock, all_db_companies):
    # 주식 정보 추출
    symbol = stock.get('symbol', 'UNKNOWN')
    name = stock.get('name', 'UNKNOWN')
    # DB 검사 (오늘 가져온 뉴스가 있으면 패스)
    existing = await check_existing_news(session, symbol, all_db_companies)
    if existing and existing.get("is_cached"):
        articles = existing["articles"]
        return {
            **stock,
            'news': articles,
            'news_status': 'success' if articles else 'no_news_found',
            'period': 'DB Cached'
        }

    # 없으면 SerpApi 키 가져오기 (.env 파일에 저장된 값)
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        print(f"Error: SERPAPI_API_KEY is not set.")
        return {**stock, 'news': [{"title": "API Key Error", "url": "#", "source": "System", "snippet": "SERPAPI_API_KEY가 설정되지 않았습니다."}], "news_status": "error"}
        
    query = f"{name} {symbol} 주식 뉴스"
    
    params = {
        "engine": "google",
        "q": query,
        "tbm": "nws",
        "tbs": "qdr:d", # 지난 24시간 이내 기사만 수집 (오전 7:30 실행 기준 전일 7:30~오늘 7:29)
        "api_key": serpapi_key,
        "num": "5" # 가져올 뉴스 기사 최대 개수
    }
    
    try:
        print(f"  [2단계] {name}({symbol}) 뉴스 수집 중 (SerpApi 사용)...")
        async with session.get("https://serpapi.com/search", params=params) as response:
            if response.status != 200:
                print(f"Error fetching news for {symbol}: HTTP {response.status}")
                return {**stock, 'news': [{"title": "API Request Error", "url": "#", "source": "System", "snippet": f"HTTP {response.status}", "thumbnail_url": ""}], "news_status": "error"}

            data = await response.json()
            
            articles = []
            if 'news_results' in data:
                # 1단계: 기본 뉴스 정보 수집
                temp_articles = []
                for item in data['news_results'][:4]:
                    temp_articles.append({
                        'title': item.get('title', '제목 없음'),
                        'url': item.get('link', '#'),
                        'source': item.get('source', 'Google News'),
                        'timestamp': item.get('date', datetime.now(KST).isoformat()),
                        'snippet': item.get('snippet', ''),
                        'thumbnail_url': item.get('thumbnail', '')
                    })
                
                # 2단계: 각 기사별 본문 전체 내용 수집 (병렬 비동기 처리)
                if temp_articles:
                    print(f"    - {name}({symbol}) 본문(MD) 수집 중...")
                    content_tasks = [fetch_full_content(session, a['url']) for a in temp_articles]
                    contents = await asyncio.gather(*content_tasks)
                    
                    for i, a in enumerate(temp_articles):
                        # 본문이 수집되면 content에 저장, 실패 시 snippet으로 대체
                        a['content'] = contents[i] if contents[i] else a.get('snippet', '')
                        articles.append(a)
                    
            status = "success" if articles else "no_news_found"
            if articles:
                print(f"  [2단계] {name}({symbol}) 뉴스 기사 수집 완료. (조회 수: {len(articles)})")
            
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
        print(f"Error scraping news for {symbol}: {e}")
        return {**stock, 'news': [{"title": "뉴스 수집 중 오류 발생", "url": "#", "source": "Error", "snippet": str(e), "thumbnail_url": ""}], "news_status": "error"}

async def main():
    if not os.path.exists('.tmp/market_data.json'):
        print("Market data not found. Run get_stock_data.py first.")
        sys.exit(1)

    with open('.tmp/market_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    # DB에서 회사 목록을 미리 전체 가져옵니다 (Company ID 매핑용)
    all_db_companies = []
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if supabase_url and supabase_key:
        headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
        try:
            async with aiohttp.ClientSession() as fetch_session:
                async with fetch_session.get(f"{supabase_url}/rest/v1/companies?select=id,symbol", headers=headers) as resp:
                    if resp.status == 200:
                        all_db_companies = await resp.json()
        except Exception:
            pass

    print("Scraping news for tickers...")
    async with aiohttp.ClientSession() as session:
        tasks = []
        for stock in data.get('kr', []) + data.get('us', []):
            tasks.append(fetch_news_for_stock(session, stock, all_db_companies))
        
        results = await asyncio.gather(*tasks)
        
    kr_news = results[:len(data.get('kr', []))]
    us_news = results[len(data.get('kr', [])):]
    
    analysis_input = {
        'timestamp': data.get('timestamp', datetime.now(KST).isoformat()),
        'kr': kr_news,
        'us': us_news
    }
    
    # DB Sync 등으로 넘어갈 수집된 뉴스 데이터 저장
    with open('.tmp/news_data.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_input, f, ensure_ascii=False, indent=2)
    print("Raw news data saved to .tmp/news_data.json")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal Error during news scraping: {e}")
        sys.exit(1)
