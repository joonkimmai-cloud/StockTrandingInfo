import os
import json
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
KST = ZoneInfo('Asia/Seoul')
from dotenv import load_dotenv

load_dotenv()

def get_relative_volume_kr():
    print("Fetching KR market data...")
    # Get KOSPI/KOSDAQ list
    krx = fdr.StockListing('KRX')
    # Filter for larger stocks to avoid noise
    krx = krx[krx['Marcap'] > 100000000000] # Top stocks > 100B KRW
    
    results = []
    # Limit to top 100 by volume initially to find RVOL spikes
    top_vol = krx.sort_values(by='Volume', ascending=False).head(100)
    
    for _, row in top_vol.iterrows():
        symbol = row['Code']
        name = row['Name']
        try:
            df = fdr.DataReader(symbol, (datetime.now(KST) - timedelta(days=30)).strftime('%Y-%m-%d'))
            if len(df) < 21: continue
            
            avg_vol = df['Volume'].iloc[:-1].tail(20).mean()
            recent_vol = df['Volume'].iloc[-1]
            rvol = recent_vol / avg_vol if avg_vol > 0 else 0
            
            results.append({
                'symbol': symbol,
                'name': name,
                'price': float(df['Close'].iloc[-1]),
                'change': float((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100),
                'rvol': float(rvol),
                'market': 'KR',
                'issued_shares': int(row.get('Stocks', 0)),
                'marcap': int(row.get('Marcap', 0)),
                'per': float(row.get('PER', 0)) if not pd.isna(row.get('PER')) else None,
                'pbr': float(row.get('PBR', 0)) if not pd.isna(row.get('PBR')) else None
            })
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            
    return sorted(results, key=lambda x: x['rvol'], reverse=True)[:10]

def get_relative_volume_us():
    print("Fetching US market data...")
    # For US, we use a pre-defined list or common high-volume tickers for demo
    # In practice, one would use a screener API. Here we'll take top S&P 500 or similar.
    # To keep it simple and fast, let's use a list of high-volume tech stocks
    tickers = ['AAPL', 'TSLA', 'NVDA', 'AMD', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX', 'INTC', 
               'PYPL', 'SQ', 'COIN', 'BA', 'DIS', 'NIO', 'PLTR', 'BABA', 'JD', 'PDD']
    
    results = []
    for ticker in tickers:
        try:
            # Use FinanceDataReader instead of yfinance for more stable data retrieval
            df = fdr.DataReader(ticker, (datetime.now(KST) - timedelta(days=30)).strftime('%Y-%m-%d'))
            if len(df) < 21: continue
            
            avg_vol = df['Volume'].iloc[:-1].tail(20).mean()
            recent_vol = df['Volume'].iloc[-1]
            rvol = recent_vol / avg_vol if avg_vol > 0 else 0
            
            results.append({
                'symbol': ticker,
                'name': ticker, # Using ticker as name for simplicity, can be updated with a mapping
                'price': float(df['Close'].iloc[-1]),
                'change': float((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100),
                'rvol': float(rvol),
                'market': 'US',
                'issued_shares': None,
                'marcap': None,
                'per': None,
                'pbr': None
            })
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            
    return sorted(results, key=lambda x: x['rvol'], reverse=True)[:10]

def main():
    print("[1단계] 전일 주식시장에서 종목 추출 시작 (한국, 미국)")
    kr_data = get_relative_volume_kr()
    print(f"  - 한국 시장 {len(kr_data)}개 종목 추출 완료")
    us_data = get_relative_volume_us()
    print(f"  - 미국 시장 {len(us_data)}개 종목 추출 완료")
    print("[1단계] 종목 추출 종료")
    
    output = {
       'timestamp': datetime.now(KST).isoformat(),
        'kr': kr_data,
        'us': us_data
    }
    
    os.makedirs('.tmp', exist_ok=True)
    with open('.tmp/market_data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("Market data saved to .tmp/market_data.json")

if __name__ == "__main__":
    main()
