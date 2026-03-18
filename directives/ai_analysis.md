# SOP: AI News Analysis and Market Prediction

## Purpose
Analyze high-volume stocks using AI to provide economist-level insights.

## Process
1. **Input**: Load `.tmp/market_data.json`.
2. **News Scraper**: 
   - Search for the stock ticker/name on financial news sites.
   - Extract the top 4 relevant news snippets using `asyncio` for speed.
3. **AI Prompt (Gemini)**:
   - **Persona**: Senior Investment Strategist / Economist.
   - **Task**: Analyze why the trading volume surged (catalysts).
   - **Macro Context**: Integrate current market trends (inflation, rates).
   - **Output Format**: JSON with `summary`, `stock_analyses` (list), and `market_prediction`.
4. **Output**: Save to `.tmp/report.json`.
