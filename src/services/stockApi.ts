export interface StockData {
  symbol: string;
  shortName: string;
  regularMarketPrice: number;
  regularMarketChangePercent: number;
  regularMarketVolume: number;
  news: any[];
}

export const fetchTopStocks = async (market: 'US' | 'KR'): Promise<StockData[]> => {
  try {
    const response = await fetch(`/api/report?market=${market}`);
    const result = await response.json();
    return result.stocks || [];
  } catch (error) {
    console.error('Error in fetchTopStocks:', error);
    return [];
  }
};
