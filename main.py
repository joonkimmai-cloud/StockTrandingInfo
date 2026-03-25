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

def db_log(step_name, status, message, error_detail=None, execution_time=None):
    """
    [기능] 각 단계가 끝날 때마다 '잘 끝났는지' 혹은 '에러가 났는지'를 인터넷 데이터베이스(Supabase)에 기록합니다.
    """
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/execution_logs"
    headers = {
        "apikey": os.getenv("SUPABASE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "step_name": step_name,       # 어떤 단계를 실행했는지 (예: 데이터 수집)
        "status": status,             # 성공(SUCCESS) 또는 실패(FAIL) 상태
        "log_message": message,       # 간략한 설명 메시지
        "error_detail": error_detail, # 에러가 났을 경우 구체적인 이유
        "execution_time": execution_time # 실행하는 데 걸린 시간
    }
    
    try:
        requests.post(url, headers=headers, json=payload)
    except Exception as e:
        print(f"데이터베이스에 로그를 남기는 데 실패했어요: {e}")

def db_update_summary(status, message, success_count=0, fail_count=0):
    """
    [기능] 오늘 하루 전체 작업이 어떻게 마무리되었는지 최종 요약 보고서를 데이터베이스에 올립니다.
    """
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/batch_summary"
    headers = {
        "apikey": os.getenv("SUPABASE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}",
        "Content-Type": "application/json"
    }
    
    # 작업 기록 파일(LOG_FILE)에서 지금까지의 모든 상세 기록을 읽어옵니다.
    full_logs = ""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                full_logs = f.read()
        except:
            full_logs = "작업 기록 파일을 읽지 못했어요."

    payload = {
        "last_run_at": datetime.now(KST).isoformat(), # 마지막으로 실행한 시간
        "last_status": status,                         # 최종 성공 여부
        "summary_message": message,                    # 한 줄 요약 메시지
        "success_count": success_count,                # 전체 중 성공한 단계 수
        "fail_count": fail_count,                      # 전체 중 실패한 단계 수
        "log_content": full_logs                       # 상세한 전체 텍스트 로그
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code not in [200, 201, 204]:
            print(f"최종 보고서를 데이터베이스에 보내지 못했어요: {resp.text}")
    except Exception as e:
        print(f"최종 보고서 전송 중 오류가 발생했어요: {e}")

def run_script(script_path, step_name):
    """
    [기능] 하나의 파이썬 파일(.py)을 실행하고, 그 결과를 실시간으로 보여주고 기록합니다.
    """
    start_time = time.time()
    log_msg = f"[{datetime.now(KST).strftime('%H:%M:%S')}] {step_name} 시작합니다! ({script_path})"
    print(log_msg, flush=True)
    
    # 로컬 컴퓨터(작업 경로)에 진행 상황을 글로 남깁니다.
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + "\n")
    
    try:
        # 1. 프로그램을 실행시키고, 거기서 나오는 글자(출력)를 실시간으로 가져옵니다.
        process = subprocess.Popen(
            [sys.executable, "-u", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        stdout_captured = []
        # 2. 프로그램이 한 줄 한 줄 말하는 내용을 화면에도 뿌리고 파일에도 저장해요.
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line, end='', flush=True)
                with open(LOG_FILE, 'a', encoding='utf-8') as f:
                    f.write(line)
                stdout_captured.append(line)
        
        process.stdout.close()
        return_code = process.wait() # 프로그램이 끝날 때까지 기다립니다.
        full_stdout = "".join(stdout_captured)
        
        # 3. 프로그램이 도중에 멈추거나 실패하면 에러를 발생시킵니다.
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, script_path, output=full_stdout)
            
        # 4. 얼마나 걸렸는지 계산해서 '성공' 로그를 남깁니다.
        elapsed = f"{int(time.time() - start_time)}초"
        db_log(step_name, "SUCCESS", f"{step_name} 작업이 성공적으로 끝났어요!", execution_time=elapsed)
        return True, full_stdout
        
    except Exception as e:
        # 에러가 났을 때 구체적으로 어디서 틀렸는지 정보를 모읍니다.
        import traceback
        error_detail = traceback.format_exc()
        error_msg = f"\n[실패 알림: {step_name}] {str(e)}\n{error_detail}"
        print(error_msg, flush=True)
        
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(error_msg + "\n")
            
        # 데이터베이스에 '실패'했다고 알려줍니다.
        db_log(step_name, "FAIL", f"{step_name} 작업 중 문제가 생겼어요.", error_detail=error_detail)
        return False, error_detail

def main():
    """
    [전체 흐름 제어] 모든 종목 분석 과정을 순서대로 하나씩 실행하는 대장 함수입니다.
    """
    start_all = time.time()
    # 작업을 시작할 때 로그 파일을 새로 만듭니다.
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"--- 분석 자동화 비서 업무 시작: {datetime.now(KST)} ---\n")
    
    # [할 일 목록] 우리가 실행해야 할 스크립트들과 그 이름이에요.
    steps = [
        ('execution/get_stock_data.py', '1단계: 종목 정보 수집'),
        ('execution/get_news_and_analyze.py', '2단계: 뉴스 수집 및 AI 분석'),
        ('execution/save_to_db.py', '3단계: 데이터베이스 저장'),
        ('execution/send_email_report.py', '4단계: 이메일 전송')
    ]
    
    success_count = 0
    fail_count = 0
    final_status = "SUCCESS"
    all_summary = []

    # 목록에 있는 일들을 하나씩 시켜봅니다.
    for path, name in steps:
        success, out = run_script(path, name)
        if success:
            success_count += 1
            all_summary.append(f"{name}: OK")
        else:
            fail_count += 1
            all_summary.append(f"{name}: 실패")
            # 1단계(수집)나 2단계(분석)처럼 중요한 일이 실패하면 뒤의 일은 하지 않고 멈춥니다.
            if name in ['1단계: 종목 정보 수집', '2단계: 뉴스 수집 및 AI 분석']:
                final_status = "FAIL"
                break
            else:
                # 덜 중요한 단계(예: 이메일 전송)만 실패하면 '부분 성공'으로 표시해요.
                final_status = "PARTIAL_SUCCESS"

    # 모든 작업에 걸린 시간을 계산합니다.
    elapsed_all = f"{int(time.time() - start_all)}초"
    summary_text = f"전체 작업을 마쳤어요! 총 {elapsed_all} 걸림. 결과: {', '.join(all_summary)}"
    print(f"\n{'='*20}\n{summary_text}\n{'='*20}")
    
    # 마지막으로 데이터베이스에 오늘 하루 성적표를 보냅니다.
    db_update_summary(final_status, summary_text, success_count, fail_count)

# 프로그램이 실행되면 가장 먼저 main() 함수를 호출합니다.
if __name__ == "__main__":
    main()
