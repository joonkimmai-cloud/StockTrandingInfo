import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def check_status():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Supabase credentials not found in env.")
        return

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }

    print("\n" + "="*50)
    print(" STOCK BATCH STATUS DASHBOARD (SUPABASE) ")
    print("="*50)

    # 1. Check Summary
    try:
        sum_url = f"{supabase_url}/rest/v1/batch_summary?order=last_run_at.desc&limit=1"
        sum_resp = requests.get(sum_url, headers=headers)
        if sum_resp.status_code == 200 and sum_resp.json():
            last = sum_resp.json()[0]
            print(f"[*] Last Run Time: {last['last_run_at']}")
            print(f"[*] Last Status  : {last['last_status']}")
            print(f"[*] Summary      : {last['summary_message']}")
        else:
            print("[!] No batch summary found.")
    except Exception as e:
        print(f"[!] Error fetching summary: {e}")

    # 2. Check Recent Step Logs
    print("\n" + "-"*30)
    print(" RECENT EXECUTION LOGS (LAST 5) ")
    print("-"*30)
    try:
        log_url = f"{supabase_url}/rest/v1/execution_logs?order=created_at.desc&limit=5"
        log_resp = requests.get(log_url, headers=headers)
        if log_resp.status_code == 200:
            logs = log_resp.json()
            for l in logs:
                status_icon = "✓" if l['status'] == 'SUCCESS' else "✗"
                time_str = l['created_at'].split('T')[1].split('.')[0] # HH:MM:SS
                print(f"[{time_str}] [{status_icon}] {l['step_name']:<15} : {l['status']}")
                if l['error_detail']:
                    print(f"    - Error: {l['error_detail'][:100]}...")
        else:
            print("[!] Failed to fetch logs.")
    except Exception as e:
        print(f"[!] Error fetching logs: {e}")

    # 3. Check Local Log File
    LOCAL_LOG = '.tmp/execution.log'
    print("\n" + "-"*30)
    print(f" LOCAL LOG FILE: {LOCAL_LOG} ")
    print("-"*30)
    if os.path.exists(LOCAL_LOG):
        # last 5 lines
        with open(LOCAL_LOG, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print("".join(lines[-5:]))
    else:
         print("[!] Local log file not found.")

    print("="*50 + "\n")

if __name__ == "__main__":
    check_status()
