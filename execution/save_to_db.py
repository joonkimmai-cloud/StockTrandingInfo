import os
import sys
import json
import requests
import argparse
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
import math

KST = ZoneInfo('Asia/Seoul')
load_dotenv()

# [기능] 다른 프로그램이 실행 중인지 확인하기 위한 락(Lock) 기능을 설정합니다.
LOCK_FILE = '.tmp/save_to_db.lock'

def check_lock():
    os.makedirs('.tmp', exist_ok=True)
    if os.path.exists(LOCK_FILE):
        file_time = os.path.getmtime(LOCK_FILE)
        if (datetime.now().timestamp() - file_time) < 3600:
            print("⚠️ 데이터베이스 저장이 이미 진행 중입니다.")
            sys.exit(0)
    with open(LOCK_FILE, 'w', encoding='utf-8') as f:
        f.write(str(os.getpid()))

def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

def sanitize(value):
    """NaN/Inf 등 JSON 비호환 float 값을 None으로 변환합니다."""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value

def get_supabase_client():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("Supabase 설정이 .env 파일에 없습니다.")
        sys.exit(1)
    return supabase_url, {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

def save_stocks():
    """1단계 및 2단계: 기업 정보와 일일 가격 지표(History)를 저장합니다."""
    if not os.path.exists('.tmp/market_data.json'):
        print("상태: market_data.json 파일이 없어 저장을 생략합니다.")
        return False

    with open('.tmp/market_data.json', 'r', encoding='utf-8') as f:
        market_data = json.load(f)
    
    url, headers = get_supabase_client()
    all_stocks = market_data.get('kr', []) + market_data.get('us', [])

    print(f"--- 기업 정보 {len(all_stocks)}건 저장 중 ---")
    for stock in all_stocks:
        # 1. 기업(Companies) 테이블 Upsert
        payload = {
            "name": stock['name'],
            "symbol": stock['symbol'],
            "market": stock['market'],
            "updated_at": datetime.now(KST).isoformat()
        }
        # yfinance 등으로 수집한 상세 정보가 있다면 추가
        for key in ['sector', 'industry', 'business_summary', 'revenue', 'operating_margins', 'net_income']:
            if key in stock: payload[key] = sanitize(stock.get(key))

        res = requests.post(f"{url}/rest/v1/companies?on_conflict=symbol", headers=headers, json=payload)
        if res.status_code in [200, 201, 204]:
            print(f"  * [{stock['symbol']}] 기업 정보 업데이트 완료.")
        else:
            print(f"  * [오류] {stock['symbol']} 기업 저장 실패: {res.text}")
        
        # 2. 기업 히스토리(Company Histories) 테이블 Insert
        get_res = requests.get(f"{url}/rest/v1/companies?symbol=eq.{stock['symbol']}&select=id", headers=headers)
        if get_res.status_code == 200 and get_res.json():
            compId = get_res.json()[0]['id']
            hist_payload = {
                "company_id": compId,
                "price": sanitize(stock.get('price')),
                "change_rate": sanitize(stock.get('change')),
                "rvol": sanitize(stock.get('rvol')),
                "marcap": stock.get('marcap'),
                "recorded_at": datetime.now(KST).isoformat()
            }
            h_res = requests.post(f"{url}/rest/v1/company_histories", headers=headers, json=hist_payload)
            if h_res.status_code in [200, 201, 204]:
                print(f"    - 히스토리 가격({stock.get('price')}) 기록 완료.")
            
    print("기업 정보 저장 완료.")
    return True

def save_news():
    """3단계 및 4단계: 수집한 뉴스 기사를 저장합니다."""
    if not os.path.exists('.tmp/news_data.json'):
        print("상태: news_data.json 파일이 없어 저장을 생략합니다.")
        return False

    with open('.tmp/news_data.json', 'r', encoding='utf-8') as f:
        news_data = json.load(f)
    
    url, headers = get_supabase_client()
    news_all = news_data.get('kr', []) + news_data.get('us', [])

    print("--- 뉴스 기사 데이터 저장 중 ---")
    for stock in news_all:
        # 기업 ID 찾기
        get_res = requests.get(f"{url}/rest/v1/companies?symbol=eq.{stock['symbol']}&select=id", headers=headers)
        if get_res.status_code == 200 and get_res.json():
            compId = get_res.json()[0]['id']
            for i, article in enumerate(stock.get('news', [])):
                if not article.get('title'): continue
                
                # 날짜 처리
                pub_date = article.get('timestamp') or datetime.now(KST).isoformat() or article.get('date')
                if not pub_date or 'ago' in str(pub_date).lower(): pub_date = datetime.now(KST).isoformat()

                news_payload = {
                    "company_id": compId,
                    "company_name": stock['name'],
                    "title": article['title'],
                    "source_url": article.get('url'),
                    "source_name": article.get('source') or article.get('source_name'),
                    "content": article.get('content'),
                    "snippet": article.get('snippet'),
                    "thumbnail_url": article.get('thumbnail'),
                    "published_at": pub_date,
                    "position": i + 1
                }
                requests.post(f"{url}/rest/v1/news_articles", headers=headers, json=news_payload)
    
    print("뉴스 데이터 저장 완료.")
    return True

def save_analysis():
    """5단계 및 6단계: AI 분석 결과를 저장합니다."""
    if not os.path.exists('.tmp/report.json'):
        print("상태: report.json 파일이 없어 저장을 생략합니다.")
        return False

    with open('.tmp/report.json', 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    url, headers = get_supabase_client()
    today = datetime.now(KST).strftime('%Y-%m-%d')

    print(f"--- AI 분석 결과 저장 중 ({today}) ---")
    
    # 1. Market Reports 저장
    market_payload = {
        "report_date": today,
        "market_summary": report.get('market_summary', ''),
        "prediction": report.get('prediction', ''),
        "created_at": datetime.now(KST).isoformat()
    }
    mr_res = requests.post(f"{url}/rest/v1/market_reports?on_conflict=report_date", headers=headers, json=market_payload)
    
    # 2. 개별 종목 분석 내역 저장
    get_mr = requests.get(f"{url}/rest/v1/market_reports?report_date=eq.{today}&select=id", headers=headers)
    if get_mr.status_code == 200 and get_mr.json():
        reportId = get_mr.json()[0]['id']
        all_analysis = report.get('kr_analysis', []) + report.get('us_analysis', [])
        
        # 이전 단계에서 가져온 market_data.json을 참고하여 심볼 매칭
        with open('.tmp/market_data.json', 'r', encoding='utf-8') as f:
            m_data = json.load(f)
            stocks_map = {s['name']: s['symbol'] for s in (m_data['kr'] + m_data['us'])}

        for item in all_analysis:
            # 이름에서 심볼 추출 시도
            name_only = item['name'].split(' (')[0] if ' (' in item['name'] else item['name']
            symbol = stocks_map.get(name_only) or item.get('symbol')
            
            if symbol:
                get_c = requests.get(f"{url}/rest/v1/companies?symbol=eq.{symbol}&select=id", headers=headers)
                if get_c.status_code == 200 and get_c.json():
                    compId = get_c.json()[0]['id']
                    sa_payload = {
                        "company_id": compId,
                        "report_id": reportId,
                        "analysis_content": item.get('analysis'),
                        "sentiment": item.get('sentiment', 'Neutral'),
                        "created_at": datetime.now(KST).isoformat()
                    }
                    requests.post(f"{url}/rest/v1/stock_analysis", headers=headers, json=sa_payload)
                    
    print("AI 분석 데이터 저장 완료.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Supabase Data Syncer')
    parser.add_argument('--stocks', action='store_true', help='Save stock info and histories')
    parser.add_argument('--news', action='store_true', help='Save news articles')
    parser.add_argument('--analysis', action='store_true', help='Save AI analysis insights')
    parser.add_argument('--all', action='store_true', help='Save everything')
    
    args = parser.parse_args()
    check_lock()
    try:
        if args.stocks or args.all: save_stocks()
        if args.news or args.all: save_news()
        if args.analysis or args.all: save_analysis()
    finally:
        remove_lock()
