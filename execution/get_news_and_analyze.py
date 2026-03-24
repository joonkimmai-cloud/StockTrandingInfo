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

LOCK_FILE = '.tmp/batch.lock'

def check_lock():
    os.makedirs('.tmp', exist_ok=True)
    if os.path.exists(LOCK_FILE):
        # 1시간 이상 된 락 파일은 무시 (데드락 방지용)
        file_time = os.path.getmtime(LOCK_FILE)
        if (datetime.now().timestamp() - file_time) < 3600:
            print("⚠️ [보안] 배치가 이미 실행 중입니다. 중복 실행을 방지하기 위해 종료합니다.")
            sys.exit(0)
    with open(LOCK_FILE, 'w', encoding='utf-8') as f:
        f.write(str(os.getpid()))

def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

def get_api_key_with_rotation():
    state_file = '.tmp/api_key_state.json'
    today = datetime.now(KST).strftime('%Y-%m-%d')
    
    # 기본값: 1번 키, 오늘 날짜
    state = {'current_index': 1, 'last_reset_date': today}
    
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                saved_state = json.load(f)
                # 날짜가 같으면 기존 상태 유지, 다르면 초기화(오늘 날짜로)
                if saved_state.get('last_reset_date') == today:
                    state = saved_state
        except Exception as e:
            print(f"Error reading api_state: {e}")

    key_env_var = f"GOOGLE_API_KEY_{state['current_index']}"
    api_key = os.getenv(key_env_var)
    
    # 환경변수가 없으면 1번 키로 폴백 시도
    if not api_key and state['current_index'] != 1:
        print(f"Warning: {key_env_var} not found, falling back to GOOGLE_API_KEY_1")
        state['current_index'] = 1
        api_key = os.getenv("GOOGLE_API_KEY_1")
        
    return api_key, state

def save_api_key_state(state):
    state_file = '.tmp/api_key_state.json'
    os.makedirs('.tmp', exist_ok=True)
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def rotate_api_key(state):
    if state['current_index'] < 3:
        state['current_index'] += 1
        print(f"  --> Rotating to API Key #{state['current_index']}...")
        save_api_key_state(state)
        return True
    return False

async def fetch_news_kr(session, stock_name, symbol):
    """Naver Finance News search for Korean stocks."""
    query = f"{stock_name} {symbol}"
    print(f"  - KR News Search: {query}")
    url = f"https://search.naver.com/search.naver?where=news&query={query}"
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200: return []
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            news_items = soup.select('.news_tit')
            news = []
            for item in news_items[:5]:
                news.append({
                    'title': item.get_text().strip(),
                    'url': item['href']
                })
            return news
    except Exception as e:
        print(f"Failed to fetch KR news for {stock_name}: {e}")
        return []

async def fetch_news_us(session, stock_name, symbol):
    """Google News search for US stocks."""
    query = f"{stock_name} {symbol}"
    print(f"  - US News Search: {query}")
    url = f"https://www.google.com/search?q={query}+stock+news&tbm=nws"
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
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
                if len(news) >= 5: break
            return news
    except Exception as e:
        print(f"Failed to fetch US news for {ticker}: {e}")
        return []

async def get_valid_gemini_model(session, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                models = data.get('models', [])
                for m in models:
                    if 'flash' in m.get('name', '').lower() and 'generateContent' in m.get('supportedGenerationMethods', []):
                        return m['name']
    except Exception as e:
        print(f"Model auto-discovery failed: {e}")
    return "models/gemini-1.5-flash"

async def generate_analysis(session, stock_data):
    print("[3단계] AI 분석 리포트 생성 시작...")
    
    while True:
        api_key, state = get_api_key_with_rotation()
        if not api_key:
            print(f"GOOGLE_API_KEY_{state['current_index']} is not set.")
            if rotate_api_key(state): continue
            else: return None
            
        model_name = await get_valid_gemini_model(session, api_key)
        print(f"  * 사용 모델: [{model_name}] (Key #{state['current_index']})")

        prompt = f"""
        당신은 세계적인 시니어 투자 전략가이자 경제학자입니다. 
        최근 거래량 급증 종목에 대해 전문 분석 리포트를 작성해 주세요.
        
        [데이터]
        {json.dumps(stock_data, ensure_ascii=False, indent=2)}
        
        [분석 가이드]
        1. 각 종목의 RVOL(상대적 거래량) 급증 원인 분석 (매크로, 뉴스, 산업 테마).
        2. 시장 전반의 요약과 향후 증시 예측 (에널리스트 톤).
        3. Sentiment (Bullish/Bearish) 명시.
        4. 분석 결과는 반드시 JSON 객체로만 출력하세요.
        
        [JSON 구조]
        {{
            "market_summary": "...",
            "kr_analysis": [ {{ "name": "...", "analysis": "...", "sentiment": "Bullish/Bearish" }} ],
            "us_analysis": [ {{ "name": "...", "analysis": "...", "sentiment": "Bullish/Bearish" }} ],
            "prediction": "..."
        }}
        """
        
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.5, "responseMimeType": "application/json"}
        }
        
        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    resp_text = await response.text()
                    print(f"Gemini API Error (Key #{state['current_index']}): {response.status}")
                    
                    # 400(Invalid/Expired) 또는 429(Rate Limit) 등일 때 로테이션 시도
                    if response.status in [400, 429, 401]:
                        if rotate_api_key(state):
                            continue
                    
                    print(resp_text)
                    return None
                    
                data = await response.json()
                text = data['candidates'][0]['content']['parts'][0]['text']
                # 저장 (성공 시 현재 상태 유지)
                save_api_key_state(state)
                return json.loads(text)
        except Exception as e:
            print(f"AI Analysis attempt failed with Key #{state['current_index']}: {e}")
            if rotate_api_key(state):
                continue
            return None

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
                    report_id = data[0]['id']
                    # 리포트가 발견되면, 연결된 종목 분석도 가져옴
                    sa_url = f"{supabase_url}/rest/v1/stock_analysis?report_id=eq.{report_id}&select=*,companies(name,market)"
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
                                comp_data = item.get('companies', {})
                                comp_name = comp_data.get('name', '알수없음')
                                market = comp_data.get('market', 'KR')
                                
                                analysis_obj = {
                                    "name": comp_name,
                                    "analysis": item.get('analysis_content', ''),
                                    "sentiment": item.get('sentiment', 'Neutral')
                                }
                                
                                if market in ['US', 'NASDAQ', 'NYSE']:
                                    result["us_analysis"].append(analysis_obj)
                                else:
                                    result["kr_analysis"].append(analysis_obj)
                            return result
    except: pass
    return None

async def main():
    check_lock()
    try:
        print("[2단계] 뉴스 수집 및 AI 분석 파이프라인 시작")
        if not os.path.exists('.tmp/market_data.json'):
            print("⚠️ 데이터 파일(market_data.json)을 찾을 수 없습니다.")
            return

        async with aiohttp.ClientSession() as session:
            # 중복 방지 체크
            cached = await check_existing_analysis(session)
            if cached:
                print("[2&3단계] (INFO) DB에 오늘 자 AI 분석 리포트가 이미 존재하여 작업을 생략합니다.")
                with open('.tmp/report.json', 'w', encoding='utf-8') as f:
                    json.dump(cached, f, ensure_ascii=False, indent=2)
                return

            if not os.path.exists('.tmp/market_data.json'):
                return
                
            with open('.tmp/market_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 뉴스 수집 병렬 처리
            kr_tasks = [fetch_news_kr(session, s['name'], s['symbol']) for s in data.get('kr', [])]
            us_tasks = [fetch_news_us(session, s['name'], s['symbol']) for s in data.get('us', [])]
            
            print("Fetching News...")
            kr_news = await asyncio.gather(*kr_tasks)
            us_news = await asyncio.gather(*us_tasks)
            
            for i, news in enumerate(kr_news): data['kr'][i]['news'] = news
            for i, news in enumerate(us_news): data['us'][i]['news'] = news
            
            # save news data separately for save_to_db.py compatibility
            with open('.tmp/news_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print("Generating AI Analysis...")
            report = await generate_analysis(session, data)
            if not report:
                print("[보안 알림] AI 분석 생성이 지연되어 대체 텍스트를 구성합니다.")
                # Fallback report with raw headlines
                report = {
                    "status": "success",
                    "market_summary": "⚠️ AI 분석 지연 (API 응답 실패). 수집된 최신 뉴스를 로우 데이터 형태로 전송합니다.",
                    "prediction": "최신 뉴스 헤드라인을 직접 참고하여 보수적인 관점으로 시장에 대응하시기 바랍니다.",
                    "kr_analysis": [],
                    "us_analysis": []
                }
                
                for s in data.get('kr', []):
                    news_titles = "\n".join([f"• {n['title']}" for n in s.get('news', [])])
                    report['kr_analysis'].append({
                        "name": f"{s['name']} ({s['symbol']})",
                        "analysis": f"[최신 뉴스]\n{news_titles if news_titles else '관련 기사 없음'}",
                        "sentiment": "Neutral"
                    })
                for s in data.get('us', []):
                    news_titles = "\n".join([f"• {n['title']}" for n in s.get('news', [])])
                    report['us_analysis'].append({
                        "name": f"{s['name']} ({s['symbol']})",
                        "analysis": f"[Recent News]\n{news_titles if news_titles else 'No news available'}",
                        "sentiment": "Neutral"
                    })
                
            with open('.tmp/report.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                
        print("[2&3단계] 수집 및 분석 종료 (report.json 저장 완료)")
    except Exception as e:
        print(f"⚠️ [보안] 프로세스 실행 중 예기치 않은 오류가 발생했습니다. (상세 내역은 로그 서버 확인)")
        # 보안을 위해 상세 에러(e)는 외부로 직접 출력하지 않거나 내부 로그에서만 관리 권장
    finally:
        remove_lock()

if __name__ == "__main__":
    asyncio.run(main())
