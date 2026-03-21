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
    krx = fdr.StockListing('KRX')
    krx = krx[krx['Marcap'] > 100000000000]
    
    results = []
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
            
    return sorted(results, key=lambda x: x['rvol'], reverse=True)[:5]

def get_relative_volume_us():
    print("Fetching US market data...")
    tickers = ['AAPL', 'TSLA', 'NVDA', 'AMD', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX', 'INTC', 
               'PYPL', 'SQ', 'COIN', 'BA', 'DIS', 'NIO', 'PLTR', 'BABA', 'JD', 'PDD']
    
    results = []
    for ticker in tickers:
        try:
            df = fdr.DataReader(ticker, (datetime.now(KST) - timedelta(days=30)).strftime('%Y-%m-%d'))
            if len(df) < 21: continue
            
            avg_vol = df['Volume'].iloc[:-1].tail(20).mean()
            recent_vol = df['Volume'].iloc[-1]
            rvol = recent_vol / avg_vol if avg_vol > 0 else 0
            
            results.append({
                'symbol': ticker,
                'name': ticker,
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
            
    return sorted(results, key=lambda x: x['rvol'], reverse=True)[:5]

def fetch_additional_info(symbol, market="US"):
    try:
        y_ticker = symbol
        if market == "KR":
            # 한국 주식은 기본적으로 KS(코스피) 시도, 정보가 없으면 KQ(코스닥) 재시도
            y_ticker = f"{symbol}.KS"
            
        info = yf.Ticker(y_ticker).info
        
        if market == "KR" and ('longBusinessSummary' not in info and 'enterpriseValue' not in info):
            y_ticker = f"{symbol}.KQ"
            info = yf.Ticker(y_ticker).info
            
        bs = info.get('longBusinessSummary')
        apc = info.get('52WeekChange')
        target_price = info.get('targetMeanPrice')
        current_price = info.get('currentPrice')
        ev = info.get('enterpriseValue')
        
        expected_return = None
        if target_price and current_price and current_price > 0:
            expected_return = ((target_price - current_price) / current_price) * 100
            
        return {
            'business_summary': bs if bs else "",
            'annual_price_change': float(apc * 100) if apc else None,
            'expected_return': float(expected_return) if expected_return else None,
            'enterprise_value': int(ev) if ev else None
        }
    except Exception as e:
        print(f"Failed to fetch additional info for {symbol}: {e}")
        return {
            'business_summary': "",
            'annual_price_change': None,
            'expected_return': None,
            'enterprise_value': None
        }

def main():
    print("[1단계] 전일 주식시장에서 종목 추출 시작 (한국, 미국)")
    kr_data = get_relative_volume_kr()
    us_data = get_relative_volume_us()
    
    print("[1단계] 추출된 종목에 대해 기업 핵심(상세) 정보 추가 수집 중...")
    for stock in kr_data:
        stock.update(fetch_additional_info(stock['symbol'], market="KR"))
    for stock in us_data:
        stock.update(fetch_additional_info(stock['symbol'], market="US"))
        
    print(f"  - 한국 시장 {len(kr_data)}개 종목 추출 및 상세정보 완료")
    print(f"  - 미국 시장 {len(us_data)}개 종목 추출 및 상세정보 완료")
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
