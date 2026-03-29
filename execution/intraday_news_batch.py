import os
import sys

# Add project root to sys.path to allow 'from execution.* import'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import asyncio
import aiohttp
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from utils import get_supabase_config, get_kst_now, log_error

# 기존 뉴스 수집 로직 재사용
from execution.get_news import fetch_news_kr, fetch_news_us

async def get_target_companies():
    """가장 최근(전일 또는 당일 새벽)에 분석된 핵심 종목 정보를 Supabase에서 가져옵니다."""
    url, headers = get_supabase_config()
    if not url:
        print("❌ Supabase 환경변수가 설정되지 않았습니다.")
        return []

    # 1. 가장 최신 리포트 ID 조회
    try:
        report_res = requests.get(f"{url}/rest/v1/market_reports?select=id,report_date&order=report_date.desc&limit=1", headers=headers)
        if report_res.status_code != 200 or not report_res.json():
            print("최신 리포트를 찾을 수 없습니다.")
            return []
        
        report_id = report_res.json()[0]['id']
        report_date = report_res.json()[0]['report_date']
        print(f"[*] 기준 리포트 일자: {report_date}")

        # 2. 해당 리포트에 속한 종목의 company_id 추출
        analysis_res = requests.get(f"{url}/rest/v1/stock_analysis?report_id=eq.{report_id}&select=company_id", headers=headers)
        if analysis_res.status_code != 200 or not analysis_res.json():
            print("리포트에 속한 종목 내역을 찾을 수 없습니다.")
            return []
        
        company_ids = list(set([str(item['company_id']) for item in analysis_res.json() if item.get('company_id')]))
        if not company_ids: return []

        # 3. company_id들을 콤마로 연결하여 in 쿼리 수행 (name, symbol, market 가져오기)
        ids_query = ",".join(company_ids)
        companies_res = requests.get(f"{url}/rest/v1/companies?id=in.({ids_query})&select=id,name,symbol,market", headers=headers)
        if companies_res.status_code == 200:
            return companies_res.json()
    except Exception as e:
        log_error("대상 종목 조회 중 오류", e)
    
    return []

def save_intraday_news(company_id, company_name, articles_raw):
    """실시간 수집된 뉴스 중 최신 2건만 Supabase에 저장 (중복 방지 용도)"""
    url, headers = get_supabase_config()
    if not url: return

    # 최대 최신 2건 배포
    articles = articles_raw[:2]
    
    for i, article in enumerate(articles):
        if not article.get('title'): continue

        # 중복 방지를 위한 사전 검색 (동일 URL이 당일 저장된 적 있는지 확인 - 필요시 고도화 가능)
        # 본 배치 목적 상 가장 최신 기준으로 덮어쓰거나 걍 포지션 기준 Insert 진행
        pub_date = article.get('timestamp') or get_kst_now().isoformat()
        if not pub_date or 'ago' in str(pub_date).lower(): pub_date = get_kst_now().isoformat()

        news_payload = {
            "company_id": company_id,
            "company_name": company_name,
            "title": article['title'],
            "source_url": article.get('url'),
            "source_name": article.get('source_name') or article.get('source'),
            "content": article.get('content'),
            "snippet": article.get('snippet'),
            "thumbnail_url": article.get('thumbnail'),
            "published_at": pub_date,
            "position": i + 1
        }
        
        # 실제 중복 에러가 날 수 있으므로(Unique Constraint 존재 유무에 따라) 그대로 Insert 합니다
        # (만약 에러가 난다면 에러 무시 하거나, UPSERT 로직 추가 가능)
        try:
            # 여기서는 편의상 Insert 시도
            resp = requests.post(f"{url}/rest/v1/news_articles", headers=headers, json=news_payload)
            # 만약 title이나 source_url 이 unique 걸려있어서 409 Conflict 나오면 넘어갑니다.
            if resp.status_code not in (200, 201) and '409' not in str(resp.status_code):
                 # print(f"뉴스 저장 실패 {resp.status_code}: {resp.text}")
                 pass
        except Exception as e:
            pass

async def main():
    print(f"[{get_kst_now().strftime('%Y-%m-%d %H:%M:%S')}] 장중 뉴스 수집 시작...")
    
    companies = await get_target_companies()
    if not companies:
        print("대상 기업이 없습니다. 배치를 종료합니다.")
        return
        
    print(f"총 {len(companies)}개 기업에 대한 뉴스 검색을 진행합니다.")

    async with aiohttp.ClientSession() as session:
        tasks = []
        for stock in companies:
            if str(stock.get('market', '')).upper() in ['KOSPI', 'KOSDAQ']:
                tasks.append(fetch_news_kr(session, stock['name'], stock['symbol']))
            else:
                tasks.append(fetch_news_us(session, stock['name'], stock['symbol']))
                
        results = await asyncio.gather(*tasks)
        
        for stock, news_list in zip(companies, results):
            if news_list:
                save_intraday_news(stock['id'], stock['name'], news_list)
                
    print(f"[{get_kst_now().strftime('%Y-%m-%d %H:%M:%S')}] 뉴스 수집 및 DB 저장 완료.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
