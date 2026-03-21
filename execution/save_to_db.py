import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
KST = ZoneInfo('Asia/Seoul')

load_dotenv()

def save_to_supabase():
    # 1. 필수 데이터 파일 확인: 주식 데이터와 뉴스 데이터가 제대로 수집되었는지 체크
    if not os.path.exists('.tmp/market_data.json') or not os.path.exists('.tmp/news_data.json'):
        print("Required data files (.tmp/market_data.json or .tmp/news_data.json) not found.")
        return

    with open('.tmp/market_data.json', 'r', encoding='utf-8') as f:
        market_data = json.load(f)
    
    with open('.tmp/news_data.json', 'r', encoding='utf-8') as f:
        news_data = json.load(f)

    all_stocks = market_data['kr'] + market_data['us']
    # news_data has 'kr' and 'us' keys containing lists of stocks with 'news' field
    news_all = news_data['kr'] + news_data['us']
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Supabase credentials not found in .env")
        return

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    print(f"Syncing data for {len(all_stocks)} companies and their news...")
    
    # 3. 데이터베이스(Supabase)에 정보를 하나씩 저장/업데이트 하는 전체 반복문
    for stock in all_stocks:
        # [과정 A] 회사(회사명, 시장, 요약 정보 등 고정값 위주) 정보를 먼저 DB에 넣거나 업데이트(Upsert)
        # 이미 존재하는 기업이면 updated_at 값 및 기타 정보가 갱신됩니다.
        company_payload = {
            "name": stock['name'],
            "symbol": stock['symbol'],
            "market": stock['market'],
            "business_summary": stock.get('business_summary'),
            "updated_at": datetime.now(KST).isoformat()
        }
        
        comp_resp = requests.post(
            f"{supabase_url}/rest/v1/companies?on_conflict=symbol",
            headers=headers,
            json=company_payload
        )
        
        if comp_resp.status_code not in [200, 201, 204]:
            print(f"Failed to upsert company {stock['name']}: {comp_resp.text}")
            continue

        # Get Company ID
        get_resp = requests.get(
            f"{supabase_url}/rest/v1/companies?symbol=eq.{stock['symbol']}&select=id",
            headers=headers
        )
        # 4. 회사 ID가 정상적으로 조회되었다면, 해당 회사의 정보를 기록합니다.
        if get_resp.status_code == 200 and get_resp.json():
            company_uuid = get_resp.json()[0]['id']
            
            # [과정 B] 매일 변동되는 상세 지표(가격, PER, 기대수익률, 기업가치 등)를 이력(history) 테이블에 따로 추가(Insert)
            history_payload = {
                "company_id": company_uuid,
                "price": stock.get('price'),
                "change_rate": stock.get('change'),
                "rvol": stock.get('rvol'),
                "marcap": stock.get('marcap'),
                "per": stock.get('per'),
                "pbr": stock.get('pbr'),
                "annual_price_change": stock.get('annual_price_change'),
                "expected_return": stock.get('expected_return'),
                "enterprise_value": stock.get('enterprise_value'),
                "recorded_at": datetime.now(KST).isoformat()
            }
            
            requests.post(
                f"{supabase_url}/rest/v1/company_histories",
                headers=headers,
                json=history_payload
            )
            
            # [과정 C] 뉴스 정보 저장
            stock_news_entry = next((s for s in news_all if s['symbol'] == stock['symbol']), None)
            if stock_news_entry and 'news' in stock_news_entry:
                
                # 각각의 뉴스 기사(보통 4개)에 대하여 반복
                for i, article in enumerate(stock_news_entry['news']):
                    # 제목이 있고 정상적인 기사인 경우에만 저장 진행
                    if article.get('title') and "**" not in article.get('title'):
                        # Supabase 테이블(news_articles) 구조에 맞게 데이터를 포장(mapping)
                        news_payload = {
                            "company_id": company_uuid,
                            "title": article['title'],
                            "source_url": article.get('url'),
                            # 기존 content 대신 SerpApi에서 가져온 섬네일, 요약 정보 등 새로운 필드를 사용!
                            "content": f"Source: {article.get('source', 'Google News')}",
                            "published_at": article.get('timestamp', datetime.now(KST).isoformat()),
                            
                            # -- 신규 추가된 확장 필드 (DB Schema 업데이트 필요) --
                            "thumbnail_url": article.get('thumbnail_url', ''), # 기사 썸네일 이미지 주소
                            "snippet": article.get('snippet', ''),             # 기사 요약본
                            "source_name": article.get('source', ''),          # 언론사 이름
                            "position": i + 1                                  # 뉴스 노출 순위 (1, 2, 3...)
                        }
                        
                        # 준비된 뉴스 데이터를 DB에 POST 요청으로 밀어넣기 (Insert)
                        requests.post(
                            f"{supabase_url}/rest/v1/news_articles",
                            headers=headers,
                            json=news_payload
                        )
                
    print("Database sync (Companies & News) completed.")

if __name__ == "__main__":
    save_to_supabase()
