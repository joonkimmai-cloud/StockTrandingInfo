import os
import json
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
KST = ZoneInfo('Asia/Seoul')
from dotenv import load_dotenv

load_dotenv()

def fetch_single_kr_stock(row):
    symbol = row['Code']
    name = row['Name']
    try:
        df = fdr.DataReader(symbol, (datetime.now(KST) - timedelta(days=35)).strftime('%Y-%m-%d'))
        if len(df) < 21: return None
        
        avg_vol = df['Volume'].iloc[:-1].tail(20).mean()
        recent_vol = df['Volume'].iloc[-1]
        rvol = recent_vol / avg_vol if avg_vol > 0 else 0
        
        price = float(df['Close'].iloc[-1])
        if price < 500: return None # penny stocks KR

        market = row.get('Market', 'KR')
        return {
            'symbol': symbol,
            'name': name,
            'price': price,
            'change': float((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100),
            'rvol': float(rvol),
            'market': market,
            'issued_shares': int(row.get('Stocks', 0)) if not pd.isna(row.get('Stocks')) else None,
            'marcap': int(row.get('Marcap', 0)) if not pd.isna(row.get('Marcap')) else None,
            'per': float(row.get('PER', 0)) if not pd.isna(row.get('PER')) else None,
            'pbr': float(row.get('PBR', 0)) if not pd.isna(row.get('PBR')) else None,
            'listing_date': str(row.get('ListingDate'))[:10] if not pd.isna(row.get('ListingDate')) else None
        }
    except:
        return None

def get_relative_volume_kr():
    print("Fetching KR market data with ThreadPool...")
    krx = fdr.StockListing('KRX')
    krx = krx[krx['Marcap'] > 100000000000]
    top_vol = krx.sort_values(by='Volume', ascending=False).head(150)
    
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_single_kr_stock, row) for _, row in top_vol.iterrows()]
        for future in as_completed(futures):
            res = future.result()
            if res: results.append(res)
            
    return sorted(results, key=lambda x: x['rvol'], reverse=True)[:10]

def fetch_single_us_stock(row):
    symbol = row['Symbol']
    name = row['Name']
    try:
        df = fdr.DataReader(symbol, (datetime.now(KST) - timedelta(days=35)).strftime('%Y-%m-%d'))
        if len(df) < 21: return None
        
        avg_vol = df['Volume'].iloc[:-1].tail(20).mean()
        recent_vol = df['Volume'].iloc[-1]
        rvol = recent_vol / avg_vol if avg_vol > 0 else 0
        
        price = float(df['Close'].iloc[-1])
        if price < 1.0: return None # penny stocks US

        return {
            'symbol': symbol,
            'name': name,
            'price': price,
            'change': float((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100),
            'rvol': float(rvol),
            'market': 'NASDAQ',
            'issued_shares': None,
            'marcap': None,
            'per': None,
            'pbr': None
        }
    except:
        return None

def get_relative_volume_us():
    print("Fetching US market data (S&P 500) with ThreadPool...")
    # NASDAQ 대신 S&P 500 리스트 활용 (약 500개 종목)
    sp500 = fdr.StockListing('S&P500')
    
    results = []
    # 500개 종목에 대해 병렬로 RVOL 계산 (S&P500은 거래량이 전반적으로 많아 유리함)
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_single_us_stock, row) for _, row in sp500.iterrows()]
        for future in as_completed(futures):
            res = future.result()
            if res: results.append(res)
            
    return sorted(results, key=lambda x: x['rvol'], reverse=True)[:10]

def fetch_additional_info(stock):
    try:
        symbol = stock['symbol']
        market = stock['market']
        y_ticker = symbol
        if market in ['KOSPI', 'KOSDAQ', 'KRX', 'KR']:
            y_ticker = f"{symbol}.KS"
            
        ticker_obj = yf.Ticker(y_ticker)
        info = ticker_obj.info
        
        # 한국 주식은 KQ 재시도
        if market in ['KOSPI', 'KOSDAQ', 'KRX', 'KR'] and ('longBusinessSummary' not in info and 'enterpriseValue' not in info):
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
            
        officers = info.get('companyOfficers', [])
        ceo = next((o['name'] for o in officers if 'Chief Executive Officer' in (o.get('title') or '')), None)
        if not ceo and officers: ceo = officers[0].get('name')
        
        founded = info.get('founded')
        list_date = stock.get('listing_date')
        if not list_date and 'firstTradeDateEpochUtc' in info:
            list_date = datetime.fromtimestamp(info['firstTradeDateEpochUtc'], KST).strftime('%Y-%m-%d')

        stock.update({
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'business_summary': info.get('longBusinessSummary') or info.get('shortBusinessSummary', ""),
            'revenue': info.get('totalRevenue'),
            'operating_margins': info.get('operatingMargins'),
            'net_income': info.get('netIncomeToCommon'),
            'website': info.get('website'),
            'city': info.get('city'),
            'ceo': ceo,
            'founded_date': str(founded) if founded else None,
            'listing_date': list_date,
            'annual_price_change': float(apc * 100) if apc else None,
            'expected_return': float(expected_return) if expected_return else None,
            'enterprise_value': int(ev) if ev else None
        })
    except Exception as e:
        # print(f"Failed to fetch additional info for {stock['symbol']}: {e}")
        stock.update({
            'sector': None,
            'industry': None,
            'business_summary': "",
            'revenue': None,
            'operating_margins': None,
            'net_income': None,
            'website': None,
            'city': None,
            'ceo': None,
            'founded_date': None,
            'listing_date': stock.get('listing_date'),
            'annual_price_change': None,
            'expected_return': None,
            'enterprise_value': None
        })
    return stock

def main():
    print("[1단계] 전일 주식시장에서 종목 추출 시작 (한국, 미국)")
    kr_data = get_relative_volume_kr()
    us_data = get_relative_volume_us()
    
    print("[1단계] 추출된 종목에 대해 기업 핵심(상세) 정보 추가 수집 중...")
    
    all_stocks = kr_data + us_data
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_additional_info, stock) for stock in all_stocks]
        for future in as_completed(futures):
            future.result()
        
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
