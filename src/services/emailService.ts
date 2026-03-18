export interface EmailConfig {
  to: string;
  from: string;
  subject: string;
  html: string;
}

export const generateEmailHtml = (summaries: any[], market: string) => {
  const cards = summaries.map(s => `
    <div style="background: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 20px; border-left: 5px solid ${s.sentiment === 'positive' ? '#10b981' : s.sentiment === 'negative' ? '#ef4444' : '#6366f1'};">
      <div style="background: rgba(255,255,255,0.1); padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; color: #f1f5f9; display: inline-block; margin-bottom: 10px;">${s.ticker}</div>
      <h3 style="color: #f1f5f9; margin: 0 0 10px 0; font-size: 18px;">${s.title}</h3>
      <p style="color: #94a3b8; line-height: 1.6; margin: 0;">${s.summary}</p>
      <div style="margin-top: 15px; font-size: 13px; color: #6366f1; font-weight: bold;">📊 Impact Score: ${s.impactScale}/10</div>
    </div>
  `).join('');

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { font-family: 'Helvetica', Arial, sans-serif; background-color: #0f172a; color: #f1f5f9; padding: 40px; }
        .container { max-width: 600px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 40px; }
        .footer { text-align: center; margin-top: 40px; font-size: 12px; color: #94a3b8; }
      </style>
    </head>
    <body style="margin:0; padding:40px; background-color:#0f172a;">
      <div class="container" style="max-width: 600px; margin: 0 auto;">
        <div class="header" style="text-align: center; margin-bottom: 40px;">
          <h1 style="color: #6366f1; margin: 0;">Daily Stock Report</h1>
          <p style="color: #94a3b8;">${market} Market Analysis - ${new Date().toLocaleDateString()}</p>
        </div>
        ${cards}
        <div class="footer" style="text-align: center; margin-top: 40px; font-size: 12px; color: #94a3b8;">
          본 메일은 매일 오전 06시(KST) 인공지능에 의해 자동으로 생성됩니다.
        </div>
      </div>
    </body>
    </html>
  `;
};
