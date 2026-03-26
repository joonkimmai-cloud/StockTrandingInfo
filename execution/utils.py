import os
import sys
import time
import math
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# [설정] 대한민국 표준시(KST)
KST = ZoneInfo('Asia/Seoul')

def get_kst_now():
    return datetime.now(KST)

class BatchLock:
    """
    배치 스크립트 중복 실행 방지를 위한 파일 락 클래스.
    """
    def __init__(self, lock_name, timeout=3600):
        self.lock_path = os.path.join('.tmp', f"{lock_name}.lock")
        self.timeout = timeout
        os.makedirs('.tmp', exist_ok=True)

    def acquire(self):
        if os.path.exists(self.lock_path):
            file_time = os.path.getmtime(self.lock_path)
            if (time.time() - file_time) < self.timeout:
                print(f"⚠️ [Lock] '{self.lock_path}'가 이미 존재하며 실행 중입니다. (기존 프로세스 종료 전까지 대기 필요)")
                return False
            else:
                print(f"⚠️ [Lock] '{self.lock_path}'가 만료되어(1시간 이상) 락을 갱신합니다.")
        
        try:
            with open(self.lock_path, 'w', encoding='utf-8') as f:
                f.write(str(os.getpid()))
            return True
        except Exception as e:
            print(f"❌ [Lock] 락 파일 생성 실패: {e}")
            return False

    def release(self):
        try:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
            return True
        except Exception as e:
            print(f"❌ [Lock] 락 파일 제거 실패: {e}")
            return False

def get_supabase_config():
    """
    Supabase 연결 정보를 관리합니다.
    """
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("❌ [Config] SUPABASE_URL 또는 SUPABASE_KEY가 설정되지 않았습니다.")
        return None, None
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    return url, headers

def sanitize_json_value(value):
    """
    NaN/Inf와 같은 JSON 비표준 float 값을 None으로 변환합니다.
    """
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value

def log_error(step_name, error):
    """
    시큐어 코딩을 준수하여 상세 스택 트레이스 대신 요약된 에러를 출력합니다.
    """
    print(f"❌ [{step_name}] 오류 발생: {str(error)}")
