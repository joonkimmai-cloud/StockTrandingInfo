import os
import subprocess
import sys
import time
import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo

# 1. 시간 설정: 대한민국 표준시(KST)를 기준으로 사용합니다.
KST = ZoneInfo('Asia/Seoul')

# 2. 환경 변수 로드: 숨겨진 설정값(.env 파일)들을 프로그램으로 가져옵니다.
from dotenv import load_dotenv
load_dotenv()

# 3. 로그 파일 설정: 프로그램이 일한 기록을 남길 장소(.tmp 폴더의 execution.log)를 만듭니다.
LOG_FILE = '.tmp/execution.log'
os.makedirs('.tmp', exist_ok=True)

def db_log(step_name, status, message, error_detail=None, execution_time=None, log_content=None):
    """
    [기능] 각 단계가 끝날 때마다 상태와 상세 콘솔 기록을 Supabase 데이터베이스에 기록합니다.
    """
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
        "execution_time": execution_time,
        "log_content": log_content # 상세 실행 내용을 여기에 담아 DB로 보냅니다.
    }
    
    try:
        requests.post(url, headers=headers, json=payload)
    except Exception as e:
        print(f"DB 로그 기록 실패: {e}")

def db_update_summary(status, message, success_count=0, fail_count=0):
    """
    [기능] 오늘 전체 작업의 최종 요약 보고서를 DB에 기록합니다.
    """
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/batch_summary"
    headers = {
        "apikey": os.getenv("SUPABASE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}",
        "Content-Type": "application/json"
    }
    
    full_logs = ""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                full_logs = f.read()
        except:
            full_logs = "로그 파일을 읽지 못했습니다."

    payload = {
        "last_run_at": datetime.now(KST).isoformat(),
        "last_status": status,
        "summary_message": message,
        "success_count": success_count,
        "fail_count": fail_count,
        "log_content": full_logs
    }
    
    try:
        requests.post(url, headers=headers, json=payload)
    except Exception as e:
        print(f"최종 요약 보고 실패: {e}")

def run_script(script_path, step_name, args=None):
    """
    [기능] 하나의 파이썬 파일을 실행하고 결과를 실시간으로 로그에 남깁니다.
    """
    if args is None: args = []
    start_time = time.time()
    log_msg = f"[{datetime.now(KST).strftime('%H:%M:%S')}] {step_name} 시작 ({script_path} {' '.join(args)})"
    print(log_msg, flush=True)
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + "\n")
    
    try:
        command = [sys.executable, "-u", script_path] + args
        process = subprocess.Popen(
            command,
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
            
        elapsed = f"{int(time.time() - start_time)}초"
        db_log(step_name, "SUCCESS", f"{step_name} 성공", execution_time=elapsed, log_content=full_stdout)
        return True, full_stdout
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        error_msg = f"\n[실패] {step_name}: {str(e)}"
        print(error_msg, flush=True)
        # 실패 시에도 지금까지 모인 stdout 내용을 함께 보냅니다.
        captured_so_far = "".join(stdout_captured)
        db_log(step_name, "FAIL", f"{step_name} 실패", error_detail=error_detail, log_content=captured_so_far)
        return False, error_detail

def main():
    """
    [전체 흐름 제어] 사용자가 요청한 7단계 순서대로 배치를 실행합니다.
    """
    start_all = time.time()
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"--- 분석 자동화 비서 업무 시작: {datetime.now(KST)} ---\n")
    
    # [할 일 목록] 7단계 순서로 재배치
    steps = [
        ('execution/get_stock_data.py', '1단계: 기업 정보 수집', []),
        ('execution/save_to_db.py', '2단계: 기업 정보 DB 저장', ['--stocks']),
        ('execution/get_news.py', '3단계: 기업 뉴스 수집', []),
        ('execution/save_to_db.py', '4단계: 뉴스 정보 DB 저장', ['--news']),
        ('execution/analyze_news.py', '5단계: 기업별 AI 분석', []),
        ('execution/save_to_db.py', '6단계: AI 분석 정보 DB 저장', ['--analysis']),
        ('execution/send_email_report.py', '7단계: 이메일 전송', [])
    ]
    
    success_count = 0
    fail_count = 0
    final_status = "SUCCESS"
    all_summary = []

    for path, name, args in steps:
        success, out = run_script(path, name, args)
        if success:
            success_count += 1
            all_summary.append(f"{name}: OK")
        else:
            fail_count += 1
            all_summary.append(f"{name}: FAIL")
            # 중요한 단계 실패 시 중단 (1~4단계는 핵심)
            if name in ['1단계: 기업 정보 수집', '3단계: 기업 뉴스 수집']:
                final_status = "FAIL"
                break
            else:
                final_status = "PARTIAL_SUCCESS"

    elapsed_all = f"{int(time.time() - start_all)}초"
    summary_text = f"작업 완료: {elapsed_all} 소요. 결과: {', '.join(all_summary)}"
    print(f"\n{summary_text}")
    db_update_summary(final_status, summary_text, success_count, fail_count)

if __name__ == "__main__":
    main()
