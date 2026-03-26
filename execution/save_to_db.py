import os
import sys
import json
import requests
import argparse
from utils import *

def save_stocks():
    """1단계 및 2단계: 기업 정보와 일일 가격 지표(History)를 저장합니다."""
    if not os.path.exists('.tmp/market_data.json'):
        print("❌ 오류: market_data.json 파일이 없어 저장을 실패했습니다. (1단계 수집 미완료)")
        return

    with open('.tmp/market_data.json', 'r', encoding='utf-8') as f:
        market_data = json.load(f)
    
    url, headers = get_supabase_config()
    all_stocks = market_data.get('kr', []) + market_data.get('us', [])

    print(f"--- 기업 정보 {len(all_stocks)}건 저장 중 ---")
    for stock in all_stocks:
        # 1. 기업(Companies) 테이블 Upsert
        payload = {
            "name": stock['name'],
            "symbol": stock['symbol'],
            "market": stock['market'],
            "updated_at": get_kst_now().isoformat()
        }
        for key in ['sector', 'industry', 'business_summary', 'revenue', 'operating_margins', 'net_income']:
            if key in stock: payload[key] = sanitize_json_value(stock.get(key))

        res = requests.post(f"{url}/rest/v1/companies?on_conflict=symbol", headers=headers, json=payload)
        
        # 2. 기업 히스토리(Company Histories) 테이블 Insert
        get_res = requests.get(f"{url}/rest/v1/companies?symbol=eq.{stock['symbol']}&select=id", headers=headers)
        if get_res.status_code == 200 and get_res.json():
            compId = get_res.json()[0]['id']
            hist_payload = {
                "company_id": compId,
                "price": sanitize_json_value(stock.get('price')),
                "change_rate": sanitize_json_value(stock.get('change')),
                "rvol": sanitize_json_value(stock.get('rvol')),
                "marcap": stock.get('marcap'),
                "recorded_at": get_kst_now().isoformat()
            }
            requests.post(f"{url}/rest/v1/company_histories", headers=headers, json=hist_payload)
            
    print("기업 정보 저장 완료.")
    return True

def save_news():
    """3단계 및 4단계: 수집한 뉴스 기사를 저장합니다."""
    if not os.path.exists('.tmp/news_data.json'):
        print("❌ 오류: news_data.json 파일이 없어 저장을 실패했습니다. (3단계 뉴스 수집 미완료)")
        return

    with open('.tmp/news_data.json', 'r', encoding='utf-8') as f:
        news_data = json.load(f)
    
    url, headers = get_supabase_config()
    news_all = news_data.get('kr', []) + news_data.get('us', [])

    print("--- 뉴스 기사 데이터 저장 중 ---")
    for stock in news_all:
        get_res = requests.get(f"{url}/rest/v1/companies?symbol=eq.{stock['symbol']}&select=id", headers=headers)
        if get_res.status_code == 200 and get_res.json():
            compId = get_res.json()[0]['id']
            for i, article in enumerate(stock.get('news', [])):
                if not article.get('title'): continue
                
                pub_date = article.get('timestamp') or get_kst_now().isoformat()
                if not pub_date or 'ago' in str(pub_date).lower(): pub_date = get_kst_now().isoformat()

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
        print("❌ 오류: report.json 파일이 없어 저장을 실패했습니다. (5단계 AI 분석 미완료)")
        return

    with open('.tmp/report.json', 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    url, headers = get_supabase_config()
    today = get_kst_now().strftime('%Y-%m-%d')

    print(f"--- AI 분석 결과 저장 중 ({today}) ---")
    
    market_payload = {
        "report_date": today,
        "market_summary": report.get('market_summary', ''),
        "investment_strategy": report.get('investment_strategy', report.get('prediction', 'No strategy provided.')),
        "prediction": report.get('prediction', ''),
        "created_at": get_kst_now().isoformat()
    }
    requests.post(f"{url}/rest/v1/market_reports?on_conflict=report_date", headers=headers, json=market_payload)
    
    get_mr = requests.get(f"{url}/rest/v1/market_reports?report_date=eq.{today}&select=id", headers=headers)
    if get_mr.status_code == 200 and get_mr.json():
        reportId = get_mr.json()[0]['id']
        all_analysis = report.get('kr_analysis', []) + report.get('us_analysis', [])
        
        if os.path.exists('.tmp/market_data.json'):
            with open('.tmp/market_data.json', 'r', encoding='utf-8') as f:
                m_data = json.load(f)
                stocks_map = {s['name']: s['symbol'] for s in (m_data['kr'] + m_data['us'])}

            for item in all_analysis:
                symbol = item.get('symbol')
                if not symbol:
                    name_only = item['name'].split(' (')[0] if ' (' in item['name'] else item['name']
                    symbol = stocks_map.get(name_only)
                
                if symbol:
                    get_c = requests.get(f"{url}/rest/v1/companies?symbol=eq.{symbol}&select=id", headers=headers)
                    if get_c.status_code == 200 and get_c.json():
                        compId = get_c.json()[0]['id']
                        sa_payload = {
                            "company_id": compId,
                            "report_id": reportId,
                            "analysis_content": item.get('analysis'),
                            "sentiment": item.get('sentiment', 'Neutral'),
                            "created_at": get_kst_now().isoformat()
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
    lock = BatchLock("save_to_db")
    if lock.acquire():
        try:
            if args.stocks or args.all: save_stocks()
            if args.news or args.all: save_news()
            if args.analysis or args.all: save_analysis()
        except Exception as e:
            log_error("DB 저장 메인", e)
        finally:
            lock.release()
