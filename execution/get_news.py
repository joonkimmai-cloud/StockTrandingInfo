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

async def fetch_article_content(session, url):
    """
    기사 원문에서 3줄 정도의 텍스트를 추출합니다.
    """
    if not url or not url.startswith('http'): return ""
    try:
        async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5) as res:
            if res.status != 200: return ""
            html = await res.text()
            soup = BeautifulSoup(html, 'html.parser')
            # 불필요한 태그 제거
            for s in soup(['script', 'style', 'header', 'footer', 'nav']): s.decompose()
            
            # 본문 텍스트 추출 시도
            text = soup.get_text(separator='\n')
            lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 20]
            return "\n".join(lines[:3]) # 3줄 정도만 반환
    except:
        return ""

async def fetch_news_kr(session, stock_name, symbol):
    """
    네이버 뉴스 검색 (한국 종목용) - 상세 정보 포함
    """
    query = f"{stock_name} 경제"
    url = f"https://search.naver.com/search.naver?where=news&query={query}&sort=1"
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200: return []
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 검색 결과 리스트 아이템 찾기
            items = soup.select('.news_wrap.api_ani_send')
            
            news = []
            for item in items:
                title_el = item.select_one('.news_tit')
                if not title_el: continue
                
                title = title_el.get_text().strip()
                link = title_el.get('href')
                
                # 상세 정보 추출
                source_name = ""
                source_el = item.select_one('.info.press')
                if source_el: source_name = source_el.get_text().strip().replace("언론사 선정", "")
                
                snippet = ""
                snippet_el = item.select_one('.api_txt_lines.dsc_txt_wrap')
                if snippet_el: snippet = snippet_el.get_text().strip()
                
                thumbnail = ""
                thumb_el = item.select_one('.thumb.api_get')
                if thumb_el: thumbnail = thumb_el.get('src')
                
                # 기사 본문 요약 (3줄) 가져오기
                content = await fetch_article_content(session, link)
                if not content: content = snippet # 본문 못 가져오면 스니펫으로 대체

                if title and link:
                    news.append({
                        'title': title, 
                        'url': link,
                        'source_name': source_name,
                        'snippet': snippet,
                        'thumbnail': thumbnail,
                        'content': content
                    })
                if len(news) >= 3: break # 너무 많으면 느려지므로 상위 3개만 심층 수집
            return news
    except Exception as e:
        print(f"한국 뉴스 수집 실패 ({stock_name}): {e}")
        return []

async def fetch_news_us(session, stock_name, symbol):
    """
    구글 뉴스 검색 (미국 종목용) - 상세 정보 포함
    """
    query = f"{stock_name} Finance"
    url = f"https://www.google.com/search?q={query}+stock+news&tbm=nws&tbs=sbd:1"
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200: return []
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 구글 뉴스 검색 결과 셀렉터 (G-card 형태)
            items = soup.select('div.SoS9Cc, div.v7wZne, div[role="listitem"]')
            
            news = []
            for item in items:
                link_el = item.select_one('a')
                title_el = item.select_one('h3, div[role="heading"]')
                if not link_el or not title_el: continue
                
                title = title_el.get_text().strip()
                link = link_el.get('href')
                if link.startswith('/url?q='):
                    link = link.split('/url?q=')[1].split('&')[0]
                
                # 상세 정보 추출
                source_name = ""
                source_el = item.select_one('div.Mg0Z9e, span.xNxY1c')
                if source_el: source_name = source_el.get_text().strip()
                
                snippet = ""
                snippet_el = item.select_one('div.GI74ad, div.VwiC3b')
                if snippet_el: snippet = snippet_el.get_text().strip()
                
                thumbnail = ""
                thumb_el = item.select_one('img')
                if thumb_el: thumbnail = thumb_el.get('src') or thumb_el.get('data-src')

                # 기사 본문 요약 (3줄) 가져오기
                content = await fetch_article_content(session, link)
                if not content: content = snippet

                if title and link:
                    news.append({
                        'title': title, 
                        'url': link,
                        'source_name': source_name,
                        'snippet': snippet,
                        'thumbnail': thumbnail,
                        'content': content
                    })
                if len(news) >= 3: break
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
