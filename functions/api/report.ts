import { createClient } from '@supabase/supabase-js';
import { GoogleGenerativeAI } from "@google/generative-ai";
import yahooFinance from 'yahoo-finance2';
import { WorkerMailer } from 'worker-mailer';

export const onRequest = async (context: any) => {
  const { env, request } = context;
  const url = new URL(request.url);
  const marketParam = url.searchParams.get('market') || 'US';
  const market = marketParam === 'KR' ? 'KR' : 'US';

  const US_TICKERS = [
    'AAPL', 'NVDA', 'TSLA', 'AMD', 'MSFT', 'AMZN', 'META', 'GOOGL', 'GOOG', 'AVGO',
    'PLTR', 'SMCI', 'COIN', 'MSTR', 'BABA', 'NFLX', 'INTC', 'MU', 'T', 'F'
  ];

  const KR_TICKERS = [
    '005930.KS', '000660.KS', '373220.KS', '207940.KS', '005380.KS', '068270.KS', '005490.KS', '051910.KS', '035420.KS', '035720.KS',
    '000270.KS', '012330.KS', '105560.KS', '055550.KS', '032830.KS', '003550.KS', '033780.KS', '015760.KS', '096770.KS', '086790.KS'
  ];

  try {
    const tickersRaw = market === 'US' ? US_TICKERS : KR_TICKERS;

    const stocksRaw = await Promise.all(
      tickersRaw.map(async (ticker) => {
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
        } catch (e) { return null; }
      })
    );

    const stocks = (stocksRaw.filter(s => s !== null) as any[])
      .sort((a, b) => b.regularMarketVolume - a.regularMarketVolume)
      .slice(0, 10);

    const genAI = new GoogleGenerativeAI(env.GEMINI_API_KEY);
    const model = genAI.getGenerativeModel({ model: "gemini-pro" });
    const allNews = stocks.flatMap(s => s.news.map((n: any) => ({ ticker: s.symbol, title: n.title, content: n.title })));

    const prompt = `AI Analyst expert mode. Pick 4 most impactful stock news from this list: ${JSON.stringify(allNews.slice(0, 20))}. Rank and summary in Korean. Output JSON ONLY. [ { ticker, title, summary, sentiment, impactScale } ]`;
    const result = await model.generateContent(prompt);
    const summaries = JSON.parse((await result.response).text().replace(/```json/g, '').replace(/```/g, '').trim());

    // 2. Save to Supabase
    const supabase = createClient(env.SUPABASE_URL, env.SUPABASE_ANON_KEY);
    await supabase.from('daily_reports').insert([{ market, stocks, summaries }]);

    // 3. Send Email (using worker-mailer)
    const emailHtml = summaries.map((s: any) => `<h3>${s.ticker}: ${s.title}</h3><p>${s.summary}</p>`).join('<hr/>');

    await WorkerMailer.send({
      host: 'smtp.gmail.com',
      port: 587,
      authType: ['login'],
      credentials: {
        username: env.GMAIL_USER,
        password: env.GMAIL_APP_PASSWORD,
      },
    }, {
      from: `"Daily Stock" <${env.GMAIL_USER}>`,
      to: 'joonkimm.ai@gmail.com',
      subject: `[Daily ${market}] Stock Analysis Report`,
      html: `
        <h1 style="color: #6366f1;">Stock News Summary - ${market}</h1>
        ${emailHtml}
        <p>Full Dashboard: https://stock-trading-top-10.pages.dev</p>
      `,
    });

    return new Response(JSON.stringify({ status: 'done', market, summaryCount: summaries.length }), { 
      headers: { 'Content-Type': 'application/json' } 
    });
  } catch (e: any) {
    return new Response(JSON.stringify({ status: 'error', error: e.message }), { 
      status: 500, 
      headers: { 'Content-Type': 'application/json' } 
    });
  }
};
