import os
import sys
import json
import asyncio
import aiohttp
from datetime import datetime
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo
from utils import *

# [설정] 네이버 뉴스 검색용 셀렉터 풀 (Fender UI 대비)
KR_NEWS_SELECTORS = {
    'title': ['a.oNXvhe7BL30eEPS64wes', '.news_tit', 'a[class*="tit"]', 'a[role="heading"]'],
    'source': ['a.DvrfF3rvIZGLS1IFDFgg', '.info.press', '.source', '.info_group .info'],
    'snippet': ['a.MnqJlFvUinTUp_vJT_xc', '.dsc_txt', '.api_txt_lines', '.news_dsc'],
    'thumbnail': ['a.fender-ui_228e3bd1 img', 'img[class*="thumb"]', 'img.tile_img', 'img']
}

async def fetch_news_kr(session, stock_name, symbol):
    """
    네이버 뉴스 검색 (한국 종목용) - 다중 셀렉터 및 RSS 폴백 지원
    """
    query = f"{stock_name} 경제"
    # 1. 일차적으로 모바일 웹 검색 시도
    url = f"https://m.search.naver.com/search.naver?where=m_news&query={query}&sort=1"
    headers = {
        'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
    }
    
    news = []
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 제목 요소 찾기 (다중 셀렉터 적용)
                title_els = []
                for sel in KR_NEWS_SELECTORS['title']:
                    title_els = soup.select(sel)
                    if title_els: break
                
                for t_el in title_els:
                    title = t_el.get_text().strip()
                    link = t_el.get('href')
                    if not link or not link.startswith('http'): continue
                    
                    # 부모 컨테이너 찾기
                    container = t_el.find_parent(class_='bx') or t_el.find_parent(class_='api_ani_send') or t_el.parent.parent
                    
                    # 소스, 스니펫, 썸네일 (다중 셀렉터 적용)
                    source_el = select_first(container, KR_NEWS_SELECTORS['source'])
                    source_name = source_el.get_text().strip().split(' ')[0] if source_el else ""
                    
                    snippet_el = select_first(container, KR_NEWS_SELECTORS['snippet'])
                    snippet = snippet_el.get_text().strip() if snippet_el else ""
                    
                    thumb_el = select_first(container, KR_NEWS_SELECTORS['thumbnail'])
                    thumbnail = (thumb_el.get('src') or thumb_el.get('data-src')) if (thumb_el and thumb_el != t_el) else ""
                    
                    content = await fetch_article_content(session, link) or snippet

                    news.append({
                        'title': title, 'url': link, 'source_name': source_name,
                        'snippet': snippet, 'thumbnail': thumbnail, 'content': content
                    })
                    if len(news) >= 3: break

        # 2. 검색 결과가 없으면 RSS 폴백 시도
        if not news:
            print(f"  * [{stock_name}] 웹 스크레이핑 결과 없음, RSS 폴백 시도...")
            import urllib.parse
            rss_query = urllib.parse.quote(stock_name)
            rss_url = f"https://news.naver.com/rss?query={rss_query}" # 실제 네이버 RSS는 검색어 쿼리를 직접 지원하지 않을 수 있으나 예시로 작성
            # 참고: 구글 뉴스 RSS는 한국어 검색 가능
            rss_url = f"https://news.google.com/rss/search?q={rss_query}&hl=ko&gl=KR&ceid=KR:ko"
            
            async with session.get(rss_url) as resp:
                if resp.status == 200:
                    xml = await resp.text()
                    rss_soup = BeautifulSoup(xml, 'xml')
                    for item in rss_soup.find_all('item')[:3]:
                        news.append({
                            'title': item.title.text,
                            'url': item.link.text,
                            'source_name': item.source.text if item.source else "Google News",
                            'snippet': "",
                            'thumbnail': "",
                            'content': item.description.text if item.description else ""
                        })
    except Exception as e:
        log_error(f"한국 뉴스 수집 ({stock_name})", e)
        
    return news


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

async def check_existing_analysis(session):
    """오늘 자 분석 결과가 이미 DB에 있는지 확인하여 중복 작업을 방지합니다."""
    url, headers = get_supabase_config()
    if not url: return None
    
    today = get_kst_now().strftime('%Y-%m-%d')
    query_url = f"{url}/rest/v1/market_reports?report_date=eq.{today}&select=*"
    
    try:
        async with session.get(query_url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return len(data) > 0
    except: pass
    return False

def select_first(soup, selectors):
    """여러 선택자 중 첫 번째로 매칭되는 요소를 반환합니다."""
    for selector in selectors:
        el = soup.select_one(selector)
        if el: return el
    return None

async def fetch_article_content(session, url):
    """기사 원문에서 핵심 텍스트를 추출합니다."""
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

# (fetch_news_us remains mostly same, but uses log_error)
async def fetch_news_us(session, stock_name, symbol):
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
                pub_date = item.pubDate.text if item.pubDate else get_kst_now().isoformat()
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
        log_error(f"미국 뉴스 수집 ({stock_name})", e)
        return []

async def main():
    lock = BatchLock("get_news")
    if not lock.acquire(): return
    
    try:
        print("[3단계] 뉴스 데이터 수집 시작...")
        if not os.path.exists('.tmp/market_data.json'):
            print("❌ 오류: 종목 정보 파일이 없습니다. (1단계 수집 미완료)")
            return

        with open('.tmp/market_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        async with aiohttp.ClientSession() as session:
            if await check_existing_analysis(session):
                print("[3단계] (INFO) DB에 오늘 자 AI 분석 리포트가 이미 존재하여 작업을 생략합니다.")
                return

            kr_tasks = [fetch_news_kr(session, s['name'], s['symbol']) for s in data.get('kr', [])]
            us_tasks = [fetch_news_us(session, s['name'], s['symbol']) for s in data.get('us', [])]
            
            kr_results = await asyncio.gather(*kr_tasks)
            us_results = await asyncio.gather(*us_tasks)
            
            for i, news in enumerate(kr_results): data['kr'][i]['news'] = news
            for i, news in enumerate(us_results): data['us'][i]['news'] = news
            
            with open('.tmp/news_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        print("[3단계] 뉴스 수집 완료 (.tmp/news_data.json)")
    except Exception as e:
        log_error("뉴스 수집 메인", e)
    finally:
        lock.release()

if __name__ == "__main__":
    asyncio.run(main())
