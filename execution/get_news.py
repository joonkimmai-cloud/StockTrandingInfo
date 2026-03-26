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

async def check_existing_analysis(session):
    # 오늘 자 분석 결과가 이미 DB에 있는지 확인합니다.
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
                if len(data) > 0:
                    return True
    except: pass
    return False

def select_first(soup, selectors):
    """여러 선택자 중 첫 번째로 매칭되는 요소를 반환합니다."""
    for selector in selectors:
        el = soup.select_one(selector)
        if el: return el
    return None

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
            for s in soup(['script', 'style', 'header', 'footer', 'nav', 'iframe']): s.decompose()
            text = soup.get_text(separator='\n')
            lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 30]
            return "\n".join(lines[:3]) 
    except:
        return ""

async def fetch_news_kr(session, stock_name, symbol):
    """
    네이버 뉴스 검색 (한국 종목용) - Fender UI 직접 타겟팅
    """
    query = f"{stock_name} 경제"
    url = f"https://m.search.naver.com/search.naver?where=m_news&query={query}&sort=1"
    headers = {
        'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
    }
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200: return []
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            title_els = soup.select('a.oNXvhe7BL30eEPS64wes') or soup.select('.news_tit, a[class*="tit"], a[role="heading"]')
            
            news = []
            for t_el in title_els:
                title = t_el.get_text().strip()
                link = t_el.get('href')
                if not link or not link.startswith('http'): continue
                container = t_el.find_parent(class_='bx') or t_el.find_parent(class_='api_ani_send') or t_el.parent.parent
                source_el = select_first(container, ['a.DvrfF3rvIZGLS1IFDFgg', '.info.press', '.source'])
                source_name = source_el.get_text().strip().split(' ')[0] if source_el else ""
                snippet_el = select_first(container, ['a.MnqJlFvUinTUp_vJT_xc', '.dsc_txt', '.api_txt_lines'])
                snippet = snippet_el.get_text().strip() if snippet_el else ""
                thumb_el = select_first(container, ['a.fender-ui_228e3bd1 img', 'img[class*="thumb"]', 'img'])
                thumbnail = (thumb_el.get('src') or thumb_el.get('data-src')) if (thumb_el and thumb_el != t_el) else ""
                content = await fetch_article_content(session, link) or snippet

                news.append({
                    'title': title, 'url': link, 'source_name': source_name,
                    'snippet': snippet, 'thumbnail': thumbnail, 'content': content
                })
                if len(news) >= 3: break 
            return news
    except Exception as e:
        print(f"한국 뉴스 수집 실패 ({stock_name}): {e}")
        return []

async def fetch_news_us(session, stock_name, symbol):
    """
    구글 뉴스 검색 (미국 종목용) - RSS 피드 사용
    """
    import urllib.parse
    query = urllib.parse.quote(f"{stock_name} stock news")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    try:
        async with session.get(url) as response:
            if response.status != 200: return []
            xml_content = await response.text()
            soup = BeautifulSoup(xml_content, 'xml')
            items = soup.find_all('item')
            news = []
            for item in items:
                title = item.title.text if item.title else ""
                link = item.link.text if item.link else ""
                if not link: continue
                source_name = item.source.text if item.source else "Google News"
                pub_date = item.pubDate.text if item.pubDate else datetime.now().isoformat()
                snippet = ""
                if item.description:
                    snippet = BeautifulSoup(item.description.text, 'html.parser').get_text().strip()
                content = await fetch_article_content(session, link) or snippet
                news.append({
                    'title': title, 'url': link, 'source_name': source_name,
                    'snippet': snippet, 'thumbnail': "", 'content': content, 'timestamp': pub_date
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
        if not os.path.exists('.tmp/market_data.json'):
            print("❌ 오류: 종목 정보 파일이 없습니다. (1단계 수집 미완료)")
            sys.exit(1)

        with open('.tmp/market_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        async with aiohttp.ClientSession() as session:
            # 중복 방지 체크
            if await check_existing_analysis(session):
                print("[3단계] (INFO) DB에 오늘 자 AI 분석 리포트가 이미 존재하여 작업을 생략합니다.")
                return

            kr_tasks = [fetch_news_kr(session, s['name'], s['symbol']) for s in data.get('kr', [])]
            us_tasks = [fetch_news_us(session, s['name'], s['symbol']) for s in data.get('us', [])]
            
            kr_news = await asyncio.gather(*kr_tasks)
            us_news = await asyncio.gather(*us_tasks)
            
            for i, news in enumerate(kr_news): data['kr'][i]['news'] = news
            for i, news in enumerate(us_news): data['us'][i]['news'] = news
            
            with open('.tmp/news_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        print("[3단계] 뉴스 수집 완료 (.tmp/news_data.json)")
    except Exception as e:
        print(f"❌ 오류: 뉴스 수집 과정에서 오류가 발생했습니다: {e}")
        sys.exit(1)
    finally:
        remove_lock()

if __name__ == "__main__":
    asyncio.run(main())
