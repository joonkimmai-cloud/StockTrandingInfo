from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import sys
import threading
import os
import queue
import time
import random
import smtplib
import requests as req_lib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Global state
batch_status = {
    "is_running": False,
    "current_logs": "",
    "last_output": ""
}

log_queue = queue.Queue()

# ─────────────────────────────────────────
# 배치 실행 관련 기존 엔드포인트
# ─────────────────────────────────────────
def run_batch_task():
    global batch_status
    batch_status["is_running"] = True
    batch_status["current_logs"] = ""
    
    try:
        process = subprocess.Popen(
            [sys.executable, "-u", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in iter(process.stdout.readline, ''):
            if line:
                batch_status["current_logs"] += line
                print(f"DEBUG: {line.strip()}")
        
        process.stdout.close()
        process.wait()
        
        batch_status["last_output"] = batch_status["current_logs"]
    except Exception as e:
        batch_status["current_logs"] += f"\nERROR: {str(e)}"
        batch_status["last_output"] = batch_status["current_logs"]
    finally:
        batch_status["is_running"] = False

@app.route('/run-batch', methods=['POST'])
def run_batch():
    if batch_status["is_running"]:
        return jsonify({"message": "Batch is already running"}), 400
    
    batch_status["current_logs"] = "> Initializing batch process...\n"
    batch_status["last_output"] = ""
    
    thread = threading.Thread(target=run_batch_task)
    thread.start()
    
    return jsonify({"message": "Batch started successfully"}), 200

@app.route('/batch-status', methods=['GET'])
def get_status():
    return jsonify({
        "is_running": batch_status["is_running"],
        "logs": batch_status["current_logs"],
        "last_output": batch_status["last_output"]
    }), 200

# ─────────────────────────────────────────
# 이메일 인증 관련 엔드포인트
# ─────────────────────────────────────────

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

def send_verification_email(to_email, code):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    msg = MIMEMultipart()
    msg['From'] = f"short game <{smtp_user}>"
    msg['To'] = to_email
    msg['Subject'] = "[short game] 이메일 인증 코드"

    body = f"""
    <html><body style="font-family:'Segoe UI',sans-serif;background:#f0f2f5;padding:30px;">
    <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
        <div style="background:linear-gradient(135deg,#004e92 0%,#000428 100%);color:#fff;padding:30px;text-align:center;">
            <h2 style="margin:0;">이메일 인증</h2>
            <p style="margin:8px 0 0;opacity:.85;">short game 구독 인증 코드입니다.</p>
        </div>
        <div style="padding:32px;text-align:center;">
            <p style="font-size:15px;color:#333;">아래 6자리 인증 코드를 입력해 주세요.</p>
            <div style="font-size:40px;font-weight:800;letter-spacing:12px;color:#004e92;
                        background:#f0f4ff;border-radius:10px;padding:18px 24px;margin:20px 0;
                        display:inline-block;">{code}</div>
            <p style="font-size:13px;color:#888;">이 코드는 <b>10분</b> 동안 유효합니다.</p>
            <p style="font-size:12px;color:#bbb;margin-top:20px;">본인이 요청하지 않은 경우 이 메일을 무시하세요.</p>
        </div>
    </div>
    </body></html>
    """
    msg.attach(MIMEText(body, 'html'))
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_user, smtp_password)
    server.send_message(msg)
    server.quit()

@app.route('/send-verify-code', methods=['POST'])
def send_verify_code():
    data = request.json
    email = (data.get('email') or '').strip().lower()

    if not email or '@' not in email:
        return jsonify({"ok": False, "error": "유효하지 않은 이메일 형식입니다."}), 400

    try:
        # 중복 이메일 확인
        check = req_lib.get(
            f"{SUPABASE_URL}/rest/v1/subscribers?email=eq.{email}&select=email",
            headers=supabase_headers()
        )
        if check.status_code == 200 and check.json():
            return jsonify({"ok": False, "duplicate": True, "error": f"'{email}' 주소는 이미 등록된 이메일입니다."}), 200

        # 6자리 인증코드 생성
        code = str(random.randint(100000, 999999))
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

        # 기존 코드 삭제 후 새 코드 저장
        req_lib.delete(f"{SUPABASE_URL}/rest/v1/email_verifications?email=eq.{email}", headers=supabase_headers())
        req_lib.post(
            f"{SUPABASE_URL}/rest/v1/email_verifications",
            headers=supabase_headers(),
            json={"email": email, "code": code, "expires_at": expires_at, "verified": False}
        )

        send_verification_email(email, code)
        return jsonify({"ok": True, "message": "인증 코드가 발송되었습니다."}), 200

    except Exception as e:
        print(f"send_verify_code error: {e}")
        return jsonify({"ok": False, "error": f"오류 발생: {str(e)}"}), 500


@app.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    email = (data.get('email') or '').strip().lower()
    code  = (data.get('code') or '').strip()

    if not email or not code:
        return jsonify({"ok": False, "error": "이메일 또는 코드가 누락되었습니다."}), 400

    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        resp = req_lib.get(
            f"{SUPABASE_URL}/rest/v1/email_verifications?email=eq.{email}&select=code,expires_at,verified",
            headers=supabase_headers()
        )

        if resp.status_code != 200 or not resp.json():
            return jsonify({"ok": False, "error": "인증 요청 정보가 없습니다. 처음부터 다시 시도해 주세요."}), 400

        record = resp.json()[0]

        if record['expires_at'] < now_iso:
            return jsonify({"ok": False, "expired": True, "error": "인증 코드가 만료되었습니다. 다시 발송해 주세요."}), 200

        if record['code'] != code:
            return jsonify({"ok": False, "error": "인증 코드가 일치하지 않습니다. 다시 확인해 주세요."}), 200

        # 인증 성공 → subscribers 등록
        req_lib.post(
            f"{SUPABASE_URL}/rest/v1/subscribers?on_conflict=email",
            headers={**supabase_headers(), "Prefer": "resolution=merge-duplicates"},
            json={"email": email}
        )
        req_lib.delete(f"{SUPABASE_URL}/rest/v1/email_verifications?email=eq.{email}", headers=supabase_headers())

        return jsonify({"ok": True, "message": "인증 완료! 구독이 등록되었습니다."}), 200

    except Exception as e:
        print(f"verify_code error: {e}")
        return jsonify({"ok": False, "error": f"오류 발생: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(port=5000)
