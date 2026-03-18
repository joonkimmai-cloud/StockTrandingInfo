import { GoogleGenerativeAI } from "@google/generative-ai";

const API_KEY = import.meta.env.VITE_GEMINI_API_KEY;
const genAI = new GoogleGenerativeAI(API_KEY);

export interface NewsSummary {
  title: string;
  ticker: string;
  summary: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  impactScale: number; // 1 to 10
}

export const analyzeNews = async (stocks: any[]): Promise<NewsSummary[]> => {
  const model = genAI.getGenerativeModel({ model: "gemini-pro" });

  // Gather all news from all top 10 stocks
  const allNews = stocks.flatMap(stock => 
    stock.news.map((n: any) => ({
      ticker: stock.symbol,
      title: n.title,
      content: n.text || n.snippet || n.title,
      publisher: n.publisher,
      link: n.link || n.url
    }))
  ).slice(0, 30); // Limit to 30 for the analysis window

  const prompt = `
    당신은 전문 주식 분석가입니다. 상위 20개 종목에 대한 최신 뉴스 목록을 제공할 것입니다.
    이 중 "오늘 증시에 가장 큰 영향을 미칠 수 있는" 가장 중요한 기사 4개를 선정하고 요청된 JSON 형식으로 요약해 주세요.
    
    기사 데이터:
    ${JSON.stringify(allNews, null, 2)}

    요청 형식:
    [
      {
        "title": "기사 제목",
        "ticker": "관련 종목 코드",
        "summary": "3문장 내외의 요약 및 오늘 증시에 어떤 영향을 줄지에 대한 전문적인 설명",
        "sentiment": "positive | negative | neutral",
        "impactScale": 1~10 (정치/경제적 영향력 크기)
      },
      ...
    ]
    
    선정된 4개 기사만 JSON 배열 형식으로 응답해 주세요. 부연 설명 없이 JSON만 작성하세요.
  `;

  try {
    const result = await model.generateContent(prompt);
    const response = await result.response;
    const text = response.text();
    
    // Clean potential markdown code blocks
    const cleanedText = text.replace(/```json/g, '').replace(/```/g, '').trim();
    
    return JSON.parse(cleanedText);
  } catch (error) {
    console.error('Error in analyzeNews:', error);
    return [];
  }
};
