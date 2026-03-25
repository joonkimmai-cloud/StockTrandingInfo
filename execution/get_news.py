import os
import sys
import json
import asyncio
import aiohttp
from datetime import datetime
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo
KST = ZoneInfo('Asia/Seoul')
from dotenv import load_dotenv

load_dotenv()

# [기능] 다른 프로그램이 실행 중인지 확인하기 위한 락(Lock) 기능을 설정합니다.
LOCK_FILE = '.tmp/get_news.lock'

def check_lock():
    os.makedirs('.tmp', exist_ok=True)
    if os.path.exists(LOCK_FILE):
        file_time = os.path.getmtime(LOCK_FILE)
        # 1시간 이상 된 락은 무시합니다.
        if (datetime.now().timestamp() - file_time) < 3600:
            print("⚠️ 뉴스 수집이 이미 진행 중입니다.")
            sys.exit(0)
    with open(LOCK_FILE, 'w', encoding='utf-8') as f:
        f.write(str(os.getpid()))

def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

async def fetch_news_kr(session, stock_name, symbol):
    """
    네이버 뉴스 검색 (한국 종목용)
    """
    # 사용자의 요청에 따라 회사명과 '경제' 키워드만 사용하여 검색합니다.
    query = f"{stock_name} 경제"
    print(f"  - 한국 뉴스 검색 중: {query}")
    url = f"https://search.naver.com/search.naver?where=news&query={query}&sort=1"
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200: return []
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            # 다양한 기사 제목 셀렉터 지원
            news_items = soup.select('.news_tit, a.oNXvhe7BL30eEPS64wes, a[class*="tit"]')
            
            news = []
            for item in news_items:
                title = item.get_text().strip()
                link = item.get('href')
                if title and link and link.startswith('http'):
                    news.append({'title': title, 'url': link})
                if len(news) >= 10: break
            return news
    except Exception as e:
        print(f"한국 뉴스 수집 실패 ({stock_name}): {e}")
        return []

async def fetch_news_us(session, stock_name, symbol):
    """
    구글 뉴스 검색 (미국 종목용)
    """
    # 사용자의 요청에 따라 회사명과 'Finance' 키워드만 사용합니다.
    query = f"{stock_name} Finance"
    print(f"  - 미국 뉴스 검색 중: {query}")
    url = f"https://www.google.com/search?q={query}+stock+news&tbm=nws&tbs=sbd:1"
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200: return []
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            news = []
            for a in soup.find_all('a'):
                h3 = a.find('h3')
                if h3:
                    title = h3.get_text().strip()
                    g_url = a['href']
                    if g_url.startswith('/url?q='):
                        g_url = g_url.split('/url?q=')[1].split('&')[0]
                    news.append({'title': title, 'url': g_url})
                if len(news) >= 10: break
            return news
    except Exception as e:
        print(f"미국 뉴스 수집 실패 ({stock_name}): {e}")
        return []

async def main():
    check_lock()
    try:
        print("[3단계] 뉴스 데이터 수집 시작...")
        # 1. 이전 단계에서 수집한 종목 리스트 파일 읽기
        if not os.path.exists('.tmp/market_data.json'):
            print("⚠️ 종목 정보 파일이 없습니다. 1단계를 먼저 실행해 주세요.")
            return

        with open('.tmp/market_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        async with aiohttp.ClientSession() as session:
            # 2. 한국 및 미국 종목들의 뉴스를 병렬(동시)로 수집합니다.
            kr_tasks = [fetch_news_kr(session, s['name'], s['symbol']) for s in data.get('kr', [])]
            us_tasks = [fetch_news_us(session, s['name'], s['symbol']) for s in data.get('us', [])]
            
            kr_news = await asyncio.gather(*kr_tasks)
            us_news = await asyncio.gather(*us_tasks)
            
            # 3. 수집된 뉴스를 기존 데이터 구조에 매핑합니다.
            for i, news in enumerate(kr_news): data['kr'][i]['news'] = news
            for i, news in enumerate(us_news): data['us'][i]['news'] = news
            
            # 4. 수집된 전체 뉴스 데이터를 파일로 저장합니다.
            with open('.tmp/news_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        print("[3단계] 뉴스 수집 완료 (.tmp/news_data.json)")
    except Exception as e:
        print(f"뉴스 수집 과정에서 오류가 발생했습니다: {e}")
    finally:
        remove_lock()

if __name__ == "__main__":
    asyncio.run(main())
