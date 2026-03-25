import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from zoneinfo import ZoneInfo
KST = ZoneInfo('Asia/Seoul')
from dotenv import load_dotenv
import requests

def get_subscribers():
    # 구독 상태가 활성(is_active가 true이거나 null인 경우)인 사람만 불러옵니다.
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/subscribers?is_active=neq.false"
    headers = {
        "apikey": os.getenv("SUPABASE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        emails = [r['email'] for r in response.json()]
        return list(set(emails + ['joonkimm.ai@gmail.com']))
    except Exception as e:
        print(f"Supabase fetch error via REST: {e}")
        return ['joonkimm.ai@gmail.com']


def build_error_html_template(data):
    # 이제 에러 템플릿도 별도로 사용하지 않지만 하위 호환성을 위해 함수만 남겨둠
    return ""

def build_html_template(data, news_data=None):
    if data.get('status') == 'error':
        raw = data.get('raw_data', {})
        err_msg = data.get('error_message', '알 수 없는 오류')
        
        data['market_summary'] = f"⚠️ AI 분석 지연 (API 응답 실패). AI가 현재 일시적인 오류를 겪고 있어 로우 데이터를 그대로 전송합니다.<br>사유: {err_msg}"
        data['prediction'] = "가장 많이 검색된 주식들의 헤드라인을 직접 참고하여 주시기 바랍니다."
        
        if 'kr_analysis' not in data: data['kr_analysis'] = []
        for stock in raw.get('kr', []):
            news_text = "<br>".join([f"• <a href='{n.get('url', '#')}' style='color:#004e92;'>{n.get('title', '')}</a>" for n in stock.get('news', [])])
            data['kr_analysis'].append({
                "name": f"{stock.get('name')} ({stock.get('symbol')})",
                "analysis": f"<b>[수집된 최신 기사 원문 제목]</b><br>{news_text}",
                "sentiment": "Neutral"
            })
            
        if 'us_analysis' not in data: data['us_analysis'] = []
        for stock in raw.get('us', []):
            news_text = "<br>".join([f"• <a href='{n.get('url', '#')}' style='color:#004e92;'>{n.get('title', '')}</a>" for n in stock.get('news', [])])
            data['us_analysis'].append({
                "name": f"{stock.get('name')} ({stock.get('symbol')})",
                "analysis": f"<b>[수집된 최신 기사 원문 제목]</b><br>{news_text}",
                "sentiment": "Neutral"
            })

    def translate_sentiment(sentiment_str):
        if not sentiment_str: return "중립 (Neutral)"
        s = str(sentiment_str).upper()
        if 'BULL' in s or 'BUY' in s:
            return "🔥 상승 우위"
        elif 'BEAR' in s or 'SELL' in s:
            return "❄️ 하락 우위"
        return f"⚖️ 중립 ({sentiment_str})"

    if not news_data: news_data = {}

    kr_html = ""
    seen_kr = set()
    for stock in data.get('kr_analysis', []):
        if stock['name'] in seen_kr: continue
        seen_kr.add(stock['name'])
        
        s_upper = str(stock.get('sentiment', '')).upper()
        sentiment_class = "bullish" if "BULL" in s_upper or "BUY" in s_upper else "bearish"
        display_sentiment = translate_sentiment(stock.get('sentiment'))
        
        # 주식 뉴스 매핑
        news_html = ""
        for n_stock in news_data.get('kr', []):
            if stock['name'] == n_stock['name'] or (n_stock['symbol'] and n_stock['symbol'] in stock['name']):
                articles = n_stock.get('news', [])
                if articles:
                    news_html = "<div style='margin-top: 15px; border-top: 1px dashed #ddd; padding-top: 10px;'>"
                    news_html += "<strong style='font-size: 0.85em; color: #555;'>📰 원문 뉴스 기사:</strong><ul style='font-size: 0.85em; margin: 5px 0; padding-left: 20px;'>"
                    for article in articles[:3]: # 상위 3개 기사만
                        if "**" not in article.get('title', ''):
                            news_html += f"<li><a href='{article.get('url', '#')}' style='color: #004e92; text-decoration: none;' target='_blank'>{article.get('title', '제목없음')}</a></li>"
                    news_html += "</ul></div>"
                break

        kr_html += f"""
        <div class="stock-card">
            <span class="sentiment {sentiment_class}">{display_sentiment}</span>
            <div class="stock-name">{stock['name']}</div>
            <div style="font-size: 0.9em; margin-top: 5px; line-height: 1.5;">{stock['analysis']}</div>
            {news_html}
        </div>
        """
        
    us_html = ""
    seen_us = set()
    for stock in data.get('us_analysis', []):
        if stock['name'] in seen_us: continue
        seen_us.add(stock['name'])

        s_upper = str(stock.get('sentiment', '')).upper()
        sentiment_class = "bullish" if "BULL" in s_upper or "BUY" in s_upper else "bearish"
        display_sentiment = translate_sentiment(stock.get('sentiment'))
        
        # 주식 뉴스 매핑
        news_html = ""
        for n_stock in news_data.get('us', []):
            if stock['name'] == n_stock['name'] or (n_stock['symbol'] and n_stock['symbol'] in stock['name']):
                articles = n_stock.get('news', [])
                if articles:
                    news_html = "<div style='margin-top: 15px; border-top: 1px dashed #ddd; padding-top: 10px;'>"
                    news_html += "<strong style='font-size: 0.85em; color: #555;'>📰 원문 뉴스 기사:</strong><ul style='font-size: 0.85em; margin: 5px 0; padding-left: 20px;'>"
                    for article in articles[:3]:
                        if "**" not in article.get('title', ''):
                            news_html += f"<li><a href='{article.get('url', '#')}' style='color: #004e92; text-decoration: none;' target='_blank'>{article.get('title', '제목없음')}</a></li>"
                    news_html += "</ul></div>"
                break

        us_html += f"""
        <div class="stock-card">
            <span class="sentiment {sentiment_class}">{display_sentiment}</span>
            <div class="stock-name">{stock['name']}</div>
            <div style="font-size: 0.9em; margin-top: 5px; line-height: 1.5;">{stock['analysis']}</div>
            {news_html}
        </div>
        """

    template = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; color: #1c1e21; margin: 0; padding: 0; }}
        .container {{ max-width: 650px; margin: 30px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #004e92 0%, #000428 100%); color: #ffffff; padding: 40px 20px; text-align: center; }}
        .content {{ padding: 30px; line-height: 1.6; }}
        .section-title {{ font-size: 1.4em; border-bottom: 3px solid #004e92; padding-bottom: 8px; margin-top: 40px; color: #004e92; font-weight: 700; }}
        .market-summary {{ background: #f8f9fa; border-left: 4px solid #004e92; padding: 20px; border-radius: 0 8px 8px 0; margin-bottom: 25px; font-size: 1.05em; }}
        .stock-card {{ border: 1px solid #e1e4e8; border-radius: 10px; padding: 20px; margin-bottom: 20px; background: #ffffff; transition: 0.3s; }}
        .stock-name {{ font-weight: bold; font-size: 1.2em; color: #1a0a54; }}
        .sentiment {{ float: right; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600; text-transform: uppercase; }}
        .bullish {{ background: #d4edda; color: #155724; }}
        .bearish {{ background: #f8d7da; color: #721c24; }}
        .prediction-box {{ background: linear-gradient(to right, #eef2f3, #8e9eab); padding: 25px; border-radius: 12px; margin-top: 40px; }}
        .footer {{ text-align: center; font-size: 0.85em; color: #65676b; padding: 30px; background: #f0f2f5; border-top: 1px solid #e1e4e8; }}
        .tag {{ display: inline-block; background: #004e92; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; margin-bottom: 5px; }}
    </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <span style="font-size: 0.9em; opacity: 0.8;">short game INSIGHTS</span>
                <h1 style="margin: 10px 0;">Daily Market Report</h1>
                <p style="margin: 0; font-size: 1.1em; opacity: 0.9;">{datetime.now(KST).strftime('%Y-%m-%d %H:%M')}</p>
            </div>
            <div class="content">
                <div class="market-summary">
                    <h4 style="margin-top: 0; color: #004e92;">Market Sentiment Summary</h4>
                    {data.get('market_summary', '데이터를 불러올 수 없습니다.')}
                </div>
                
                <h2 class="section-title">🇰🇷 KOREA - Top Relative Volume</h2>
                {kr_html if kr_html.strip() else '<p style="color: #888; text-align: center; padding: 20px;">대한민국 시장에서 금일 조건에 부합하는 종목이 발견되지 않았습니다.</p>'}
                
                <h2 class="section-title">🇺🇸 USA - Top Relative Volume</h2>
                {us_html if us_html.strip() else '<p style="color: #888; text-align: center; padding: 20px;">미국 시장에서 금일 조건에 부합하는 종목이 발견되지 않았습니다.</p>'}
                
                <div class="prediction-box">
                    <h3 style="margin-top: 0; color: #2c3e50;">Tomorrow's Outlook & Strategy</h3>
                    <p>{data.get('prediction', '예측 데이터를 생성할 수 없습니다.')}</p>
                </div>
            </div>
            <div class="footer">
                <p>본 고지사항은 투자 참고용이며 최종 투자 결정은 본인의 판단하에 이루어져야 합니다.<br>short game Team</p>
                <div style="margin-top: 15px;">
                    <a href="#" style="color: #004e92; text-decoration: none;">Unsubscribe</a> | <a href="#" style="color: #004e92; text-decoration: none;">View Online</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return template

def send_email(subject, body, to_emails):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)

        for to_email in to_emails:
            msg = MIMEMultipart()
            msg['From'] = f"short game Report <{smtp_user}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            server.send_message(msg)
            print(f"Sent successfully to {to_email}")

        server.quit()
    except Exception as e:
        print(f"Email dispatch error: {e}")

def main():
    if not os.path.exists('.tmp/report.json'):
        print("Analysis report not found. Run get_news_and_analyze.py first.")
        return

    with open('.tmp/report.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    news_data = {}
    if os.path.exists('.tmp/news_data.json'):
        with open('.tmp/news_data.json', 'r', encoding='utf-8') as f:
            news_data = json.load(f)

    html_content = build_html_template(data, news_data)
    subscribers = get_subscribers()
    
    print(f"Starting email dispatch to {len(subscribers)} recipients...")
    send_email(f"[Stock Report] {datetime.now(KST).strftime('%Y-%m-%d')} 시장 분석 및 예측", html_content, subscribers)

if __name__ == "__main__":
    load_dotenv()
    main()
