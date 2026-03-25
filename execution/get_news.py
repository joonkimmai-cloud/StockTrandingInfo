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
    # 네이버 뉴스 링크(news.naver.com)인 경우와 일반 언론사 링크 구분하여 처리하면 더 좋지만, 
    # 일반적인 접근법으로 텍스트를 추출합니다.
    try:
        async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5) as res:
            if res.status != 200: return ""
            html = await res.text()
            soup = BeautifulSoup(html, 'html.parser')
            # 불필요한 태그 제거
            for s in soup(['script', 'style', 'header', 'footer', 'nav', 'iframe']): s.decompose()
            
            # 본문 텍스트 추출 시도 (가장 긴 텍스트 블록 위주)
            text = soup.get_text(separator='\n')
            lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 30]
            # 상단 광고나 메뉴 등을 피하기 위해 어느 정도 길이 이상의 유효한 문장만 선택
            return "\n".join(lines[:3]) # 3줄 정도만 반환
    except:
        return ""

async def fetch_news_kr(session, stock_name, symbol):
    """
    네이버 뉴스 검색 (한국 종목용) - Fender UI 직접 타겟팅 (가장 확실한 방법)
    """
    query = f"{stock_name} 경제"
    url = f"https://m.search.naver.com/search.naver?where=m_news&query={query}&sort=1"
    
    headers = {
        'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
    }
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200: return []
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. 제목 요소를 직접 찾기 (Fender UI 해시 클래스)
            title_els = soup.select('a.oNXvhe7BL30eEPS64wes')
            
            if not title_els:
                # 해시 클래스가 바뀌었을 가능성 대비 (폴백)
                title_els = soup.select('.news_tit, a[class*="tit"], a[role="heading"]')
                
            if not title_els:
                # [디버그용] 여전히 없으면 HTML 저장 후 종료
                with open('.tmp/debug_naver_fail.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                return []
            
            news = []
            for t_el in title_els:
                title = t_el.get_text().strip()
                link = t_el.get('href')
                if not link or not link.startswith('http'): continue
                
                # 해당 제목의 부모 컨테이너 찾기 (보통 bx 또는 div)
                container = t_el.find_parent(class_='bx') or t_el.find_parent(class_='api_ani_send') or t_el.parent.parent
                
                # 2. 언론사명 추출
                source_name = ""
                source_el = select_first(container, ['a.DvrfF3rvIZGLS1IFDFgg', '.info.press', '.source'])
                if source_el: source_name = source_el.get_text().strip().split(' ')[0]
                
                # 3. 요약문(Snippet) 추출
                snippet = ""
                snippet_el = select_first(container, ['a.MnqJlFvUinTUp_vJT_xc', '.dsc_txt', '.api_txt_lines'])
                if snippet_el: snippet = snippet_el.get_text().strip()
                
                # 4. 썸네일 추출
                thumbnail = ""
                thumb_el = select_first(container, ['a.fender-ui_228e3bd1 img', 'img[class*="thumb"]', 'img'])
                if thumb_el and thumb_el != t_el: # 제목 링크 자체가 이미지가 아닐 때
                    thumbnail = thumb_el.get('src') or thumb_el.get('data-src')
                
                # 기사 본문 요약 (3줄) 가져오기
                content = await fetch_article_content(session, link)
                if not content: content = snippet

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
        print(f"한국 뉴스 수집 실패 ({stock_name}): {e}")
        return []
    except Exception as e:
        print(f"한국 뉴스 수집 실패 ({stock_name}): {e}")
        return []
    except Exception as e:
        print(f"한국 뉴스 수집 실패 ({stock_name}): {e}")
        return []

async def fetch_news_us(session, stock_name, symbol):
    """
    구글 뉴스 검색 (미국 종목용) - RSS 피드 사용 (가장 안정적)
    """
    import urllib.parse
    query = urllib.parse.quote(f"{stock_name} stock news")
    # RSS 피드는 봇 차단이 적고 구조화된 데이터를 제공함
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    
    try:
        async with session.get(url) as response:
            if response.status != 200: return []
            xml_content = await response.text()
            soup = BeautifulSoup(xml_content, 'xml') # XML 파서 사용
            
            items = soup.find_all('item')
            news = []
            for item in items:
                title = item.title.text if item.title else ""
                link = item.link.text if item.link else ""
                if not link: continue
                
                source_name = item.source.text if item.source else "Google News"
                pub_date = item.pubDate.text if item.pubDate else datetime.now().isoformat()
                
                # Snippet (Description에서 HTML 태그 제거)
                snippet = ""
                if item.description:
                    snippet_soup = BeautifulSoup(item.description.text, 'html.parser')
                    snippet = snippet_soup.get_text().strip()
                
                # 상세 정보 추출 (본문 요약 및 썸네일 시도)
                content = await fetch_article_content(session, link)
                if not content: content = snippet
                
                # RSS에서는 썸네일이 바로 안 나오므로 본문에서 찾거나 빈 값
                thumbnail = "" 

                news.append({
                    'title': title, 
                    'url': link,
                    'source_name': source_name,
                    'snippet': snippet,
                    'thumbnail': thumbnail,
                    'content': content,
                    'timestamp': pub_date
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
