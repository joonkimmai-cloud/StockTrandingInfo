import { fetchTopStocks } from './stockApi';
import { analyzeNews } from './geminiService';
import { saveReport } from './supabase';
import { generateEmailHtml } from './emailService';
// worker-mailer would be used in the actual function environment

export const executeDailyReport = async (market: 'US' | 'KR') => {
  console.log(`Starting ${market} report...`);
  
  // 1. Fetch Top 10 Stocks
  const stocks = await fetchTopStocks(market);
  if (stocks.length === 0) throw new Error("No stocks found");

  // 2. AI Analysis
  const summaries = await analyzeNews(stocks);
  if (summaries.length === 0) throw new Error("AI analysis failed");

  // 3. Save to Supabase
  await saveReport({
    market,
    date: new Date().toISOString().split('T')[0],
    stocks,
    summaries
  });

  // 4. Generate Email HTML
  const html = generateEmailHtml(summaries, market);
  
  return {
    status: 'success',
    market,
    summaryCount: summaries.length,
    html
  };
};
