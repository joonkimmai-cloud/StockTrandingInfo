export interface NewsSummary {
  title: string;
  ticker: string;
  summary: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  impactScale: number;
}

export const analyzeNews = async (stocks: any[]): Promise<NewsSummary[]> => {
  // We'll trigger the backend report function which handles analysis
  try {
    const response = await fetch(`/api/report?market=${stocks[0]?.symbol?.endsWith('.KS') ? 'KR' : 'US'}`);
    const result = await response.json();
    return result.summaries || [];
  } catch (error) {
    console.error('Error in analyzeNews:', error);
    return [];
  }
};
