import yahooFinance from 'yahoo-finance2';

// In a real project, we would use a more robust "Most Active" API.
// For now, we'll fetch a broad list of high-liquidity stocks and sort them by volume.

const US_TICKERS = [
  'AAPL', 'NVDA', 'TSLA', 'AMD', 'MSFT', 'AMZN', 'META', 'GOOGL', 'GOOG', 'AVGO',
  'PLTR', 'SMCI', 'COIN', 'MSTR', 'BABA', 'NFLX', 'INTC', 'MU', 'T', 'F'
];

const KR_TICKERS = [
  '005930.KS', // Samsung Electronics
  '000660.KS', // SK Hynix
  '373220.KS', // LG Energy Solution
  '207940.KS', // Samsung Biologics
  '005380.KS', // Hyundai Motor
  '068270.KS', // Celltrion
  '005490.KS', // POSCO Holdings
  '051910.KS', // LG Chem
  '035420.KS', // NAVER
  '035720.KS', // Kakao
  '000270.KS', // Kia
  '012330.KS', // Hyundai Mobis
  '105560.KS', // KB Financial Group
  '055550.KS', // Shinhan Financial Group
  '032830.KS', // Samsung Life Insurance
  '003550.KS', // LG
  '033780.KS', // KT&G
  '015760.KS', // Korea Electric Power
  '096770.KS', // SK Innovation
  '086790.KS'  // Hana Financial Group
];

export interface StockData {
  symbol: string;
  shortName: string;
  regularMarketPrice: number;
  regularMarketChangePercent: number;
  regularMarketVolume: number;
  news: any[];
}

export const fetchTopStocks = async (market: 'US' | 'KR'): Promise<StockData[]> => {
  const tickers = market === 'US' ? US_TICKERS : KR_TICKERS;
  
  try {
    const results = await Promise.all(
      tickers.map(async (ticker) => {
        try {
          const quote = await (yahooFinance as any).quote(ticker);
          const news = await (yahooFinance as any).search(ticker, { newsCount: 3 });
          
          return {
            symbol: ticker,
            shortName: quote.shortName || ticker,
            regularMarketPrice: quote.regularMarketPrice || 0,
            regularMarketChangePercent: quote.regularMarketChangePercent || 0,
            regularMarketVolume: quote.regularMarketVolume || 0,
            news: news.news || []
          };
        } catch (e) {
          console.error(`Error fetching ${ticker}:`, e);
          return null;
        }
      })
    );

    // Filter nulls and sort by volume descending, then take top 10
    return (results.filter(r => r !== null) as StockData[])
      .sort((a, b) => b.regularMarketVolume - a.regularMarketVolume)
      .slice(0, 10);
  } catch (error) {
    console.error('Error in fetchTopStocks:', error);
    return [];
  }
};
