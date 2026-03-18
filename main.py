import os
import subprocess
import sys
import time
from datetime import datetime

def run_script(script_path):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Executing {script_path}...")
    try:
        # Use sys.executable to ensure we use the same python interpreter
        result = subprocess.run([sys.executable, script_path], check=True, capture_output=True, text=True)
        print(f"Output:\n{result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing {script_path}:")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False

def main():
    print("="*50)
    print(f"STOCK TRADING AUTOMATION - BATCH START: {datetime.now()}")
    print("="*50)
    
    # 1. Collect Stock Data (Relative Volume)
    if not run_script('execution/get_stock_data.py'):
        print("Stopping due to error in data collection.")
        return

    # 2. Analyze News and Generate Predictions
    if not run_script('execution/get_news_and_analyze.py'):
        print("Stopping due to error in AI analysis.")
        return

    # 3. Dispatch Email Reports
    if not run_script('execution/send_email_report.py'):
        print("Stopping due to error in email dispatch.")
        return

    print("="*50)
    print(f"BATCH COMPLETED SUCCESSFULLY AT {datetime.now()}")
    print("="*50)

if __name__ == "__main__":
    main()
