import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
KST = ZoneInfo('Asia/Seoul')

load_dotenv()

def save_to_supabase():
    # 1. Check required data
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
    
    for stock in all_stocks:
        # 1. Upsert Company
        company_payload = {
            "name": stock['name'],
            "symbol": stock['symbol'],
            "market": stock['market'],
            "issued_shares": stock.get('issued_shares'),
            "marcap": stock.get('marcap'),
            "per": stock.get('per'),
            "pbr": stock.get('pbr'),
            "updated_at": datetime.now(KST).isoformat()
        }
        
        comp_resp = requests.post(
            f"{supabase_url}/rest/v1/companies",
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
        if get_resp.status_code == 200 and get_resp.json():
            company_uuid = get_resp.json()[0]['id']
            
            # Find news for this stock
            stock_news_entry = next((s for s in news_all if s['symbol'] == stock['symbol']), None)
            if stock_news_entry and 'news' in stock_news_entry:
                for article in stock_news_entry['news']:
                    if article.get('title') and article.get('title') != "No recent news found":
                        news_payload = {
                            "company_id": company_uuid,
                            "title": article['title'],
                            "source_url": article.get('url'),
                            "content": f"Source: {article.get('source', 'Google News')}",
                            "published_at": article.get('timestamp', datetime.now(KST).isoformat())
                        }
                        # Simple insert for news (could check for duplicates by title if needed)
                        requests.post(
                            f"{supabase_url}/rest/v1/news_articles",
                            headers=headers,
                            json=news_payload
                        )
                
    print("Database sync (Companies & News) completed.")

if __name__ == "__main__":
    save_to_supabase()
