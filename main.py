import os
import subprocess
import sys
import time
import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo
KST = ZoneInfo('Asia/Seoul')
from dotenv import load_dotenv

load_dotenv()

# Logger settings
LOG_FILE = '.tmp/execution.log'
os.makedirs('.tmp', exist_ok=True)

def db_log(step_name, status, message, error_detail=None, execution_time=None):
    """Log execution status to Supabase."""
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/execution_logs"
    headers = {
        "apikey": os.getenv("SUPABASE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "step_name": step_name,
        "status": status,
        "log_message": message,
        "error_detail": error_detail,
        "execution_time": execution_time
    }
    
    try:
        requests.post(url, headers=headers, json=payload)
    except Exception as e:
        print(f"Failed to log to DB: {e}")

def db_update_summary(status, message, success_count=0, fail_count=0):
    """Update batch summary to Supabase with full logs."""
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/batch_summary"
    headers = {
        "apikey": os.getenv("SUPABASE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}",
        "Content-Type": "application/json"
    }
    
    # Read full execution log from file
    full_logs = ""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                full_logs = f.read()
        except:
            full_logs = "Failed to read log file."

    payload = {
        "last_run_at": datetime.now(KST).isoformat(),
        "last_status": status,
        "summary_message": message,
        "success_count": success_count,
        "fail_count": fail_count,
        "log_content": full_logs  # New field for persistent logs
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code not in [200, 201, 204]:
            print(f"Failed to update summary to DB: {resp.text}")
    except Exception as e:
        print(f"Failed to update summary to DB: {e}")

def run_script(script_path, step_name):
    start_time = time.time()
    log_msg = f"[{datetime.now(KST).strftime('%H:%M:%S')}] Executing {script_path}..."
    print(log_msg, flush=True)
    
    # Save to local file
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + "\n")
    
    try:
        # Use Popen to stream output in real-time
        process = subprocess.Popen(
            [sys.executable, "-u", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        stdout_captured = []
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line, end='', flush=True)
                with open(LOG_FILE, 'a', encoding='utf-8') as f:
                    f.write(line)
                stdout_captured.append(line)
        
        process.stdout.close()
        return_code = process.wait()
        full_stdout = "".join(stdout_captured)
        
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, script_path, output=full_stdout)
            
        elapsed = f"{int(time.time() - start_time)} seconds"
        db_log(step_name, "SUCCESS", f"Completed {step_name}", execution_time=elapsed)
        return True, full_stdout
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        error_msg = f"\n[FAILED: {step_name}] {str(e)}\n{error_detail}"
        print(error_msg, flush=True)
        
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(error_msg + "\n")
            
        db_log(step_name, "FAIL", f"Failed {step_name}", error_detail=error_detail)
        return False, error_detail

def main():
    start_all = time.time()
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"--- BATCH START: {datetime.now(KST)} ---\n")
    
    steps = [
        ('execution/get_stock_data.py', 'Data Collection'),
        ('execution/get_news_and_analyze.py', 'News & AI Analysis'),
        ('execution/save_to_db.py', 'DB Sync'),
        ('execution/send_email_report.py', 'Email Dispatch')
    ]
    
    success_count = 0
    fail_count = 0
    final_status = "SUCCESS"
    all_summary = []

    for path, name in steps:
        success, out = run_script(path, name)
        if success:
            success_count += 1
            all_summary.append(f"{name}: OK")
        else:
            fail_count += 1
            all_summary.append(f"{name}: FAILED")
            if name in ['Data Collection', 'News & AI Analysis']: # Critical steps
                final_status = "FAIL"
                break
            else:
                final_status = "PARTIAL_SUCCESS"

    elapsed_all = f"{int(time.time() - start_all)}s"
    summary_text = f"Batch finished in {elapsed_all}. Status: {', '.join(all_summary)}"
    print(f"\n{'='*20}\n{summary_text}\n{'='*20}")
    
    db_update_summary(final_status, summary_text, success_count, fail_count)

if __name__ == "__main__":
    main()
