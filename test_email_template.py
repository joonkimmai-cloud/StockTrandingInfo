import os
import json
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'execution'))

from execution.send_email_report import build_html_template

def main():
    if not os.path.exists('.tmp/report.json'):
        print("Analysis report not found.")
        return

    with open('.tmp/report.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    news_data = {}
    if os.path.exists('.tmp/news_data.json'):
        with open('.tmp/news_data.json', 'r', encoding='utf-8') as f:
            news_data = json.load(f)
            
    try:
        html_content = build_html_template(data, news_data)
        
        with open('.tmp/test_report.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("Generated .tmp/test_report.html successfully!")
    except Exception as e:
        print(f"Error generating template: {e}")

if __name__ == "__main__":
    main()
