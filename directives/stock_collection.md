# SOP: Stock Data Collection

## Purpose
Collect top 10 stocks by **Relative Volume (RVOL)** for both KR and US markets.

## Process
1. **Source**: Use `FinanceDataReader` for KR (KOSPI/KOSDAQ) and `yfinance` for US (NASDAQ/NYSE).
2. **Calculation**:
   - Get the last 21 trading days of data.
   - Calculate the average volume of the first 20 days.
   - Compare with the most recent day's volume: `RVOL = Recent Volume / Avg 20-Day Volume`.
3. **Filtering**:
   - Exclude stocks with price < $1 (Penny stocks).
   - Exclude stocks with extremely low average volume to avoid manipulation.
4. **Sorting**: Sort by RVOL descending.
5. **Output**: Save the top 10 for each market to `.tmp/market_data.json`.
