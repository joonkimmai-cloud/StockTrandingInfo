import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv
import requests

def get_subscribers():
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/subscribers"
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
    raw = data.get('raw_data', {})
    error_msg = data.get('error_message', '알 수 없는 오류')
    
    def format_stocks(stocks):
        html = ""
        for s in stocks:
            news_list = "".join([f"<li>{n}</li>" for n in s.get('news', [])])
            html += f"""
            <div class="stock-card">
                <div class="stock-name">{s['name']} ({s['symbol']})</div>
                <div style="font-size: 0.9em; margin-top: 5px;">
                    <strong>수집된 기사:</strong>
                    <ul>{news_list}</ul>
                </div>
            </div>
            """
        return html

    kr_html = format_stocks(raw.get('kr', []))
    us_html = format_stocks(raw.get('us', []))

    template = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #fce8e6; color: #1c1e21; margin: 0; padding: 0; }}
        .container {{ max-width: 650px; margin: 30px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }}
        .header {{ background: #d93025; color: #ffffff; padding: 30px 20px; text-align: center; }}
        .content {{ padding: 30px; line-height: 1.6; }}
        .section-title {{ font-size: 1.4em; border-bottom: 3px solid #d93025; padding-bottom: 8px; margin-top: 40px; color: #d93025; font-weight: 700; }}
        .error-box {{ background: #fdf2f2; border: 1px solid #f8b4b4; padding: 20px; border-radius: 8px; margin-bottom: 25px; color: #9b1c1c; }}
        .stock-card {{ border: 1px solid #e1e4e8; border-radius: 10px; padding: 15px; margin-bottom: 15px; background: #fff; }}
        .stock-name {{ font-weight: bold; font-size: 1.1em; color: #1c1e21; }}
        .footer {{ text-align: center; font-size: 0.85em; color: #65676b; padding: 30px; background: #f0f2f5; }}
    </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>AI 분석 일시 중단 안내</h1>
                <p>시스템 오류로 분석 리포트 생성이 제한되었습니다.</p>
            </div>
            <div class="content">
                <div class="error-box">
                    <strong>분석 실패 사유:</strong><br>
                    {error_msg}
                </div>
                <p>AI 분석 및 요약은 완료하지 못했으나, 수집된 주요 종목과 관련 기사 목록을 전달드립니다.</p>
                
                <h2 class="section-title">KOREA - 데이터 수집 결과</h2>
                {kr_html}
                
                <h2 class="section-title">USA - 데이터 수집 결과</h2>
                {us_html}
            </div>
            <div class="footer">
                <p>이 메일은 시스템에 의해 자동으로 발송되었습니다.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return template

def build_html_template(data):
    if data.get('status') == 'error':
        return build_error_html_template(data)

    kr_html = ""
    for stock in data.get('kr_analysis', []):
        sentiment_class = "bullish" if "Bull" in stock['sentiment'] else "bearish"
        kr_html += f"""
        <div class="stock-card">
            <span class="sentiment {sentiment_class}">{stock['sentiment']}</span>
            <div class="stock-name">{stock['name']}</div>
            <div style="font-size: 0.9em; margin-top: 5px;">{stock['analysis']}</div>
        </div>
        """
        
    us_html = ""
    for stock in data.get('us_analysis', []):
        sentiment_class = "bullish" if "Bull" in stock['sentiment'] else "bearish"
        us_html += f"""
        <div class="stock-card">
            <span class="sentiment {sentiment_class}">{stock['sentiment']}</span>
            <div class="stock-name">{stock['name']}</div>
            <div style="font-size: 0.9em; margin-top: 5px;">{stock['analysis']}</div>
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
                <span style="font-size: 0.9em; opacity: 0.8;">ALPHA TRADING INSIGHTS</span>
                <h1 style="margin: 10px 0;">Daily Market Report</h1>
                <p style="margin: 0; font-size: 1.1em; opacity: 0.9;">{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            </div>
            <div class="content">
                <div class="market-summary">
                    <h4 style="margin-top: 0; color: #004e92;">Market Sentiment Summary</h4>
                    {data.get('market_summary', '데이터를 불러올 수 없습니다.')}
                </div>
                
                <h2 class="section-title">KOREA - Top Relative Volume</h2>
                {kr_html if kr_html else '<p>금일 특이 종목이 발견되지 않았습니다.</p>'}
                
                <h2 class="section-title">USA - Top Relative Volume</h2>
                {us_html if us_html else '<p>금일 특이 종목이 발견되지 않았습니다.</p>'}
                
                <div class="prediction-box">
                    <h3 style="margin-top: 0; color: #2c3e50;">Tomorrow's Outlook & Strategy</h3>
                    <p>{data.get('prediction', '예측 데이터를 생성할 수 없습니다.')}</p>
                </div>
            </div>
            <div class="footer">
                <p>본 고지사항은 투자 참고용이며 최종 투자 결정은 본인의 판단하에 이루어져야 합니다.<br>Stock Trading Top 10 Team</p>
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
            msg['From'] = f"Stock Alpha Report <{smtp_user}>"
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

    html_content = build_html_template(data)
    subscribers = get_subscribers()
    
    print(f"Starting email dispatch to {len(subscribers)} recipients...")
    send_email(f"[Stock Report] {datetime.now().strftime('%Y-%m-%d')} 시장 분석 및 예측", html_content, subscribers)

if __name__ == "__main__":
    load_dotenv()
    main()
