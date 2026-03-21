/*
   index.js
   이메일 구독 플로우:
   1. 이메일 입력 → 구독 버튼 클릭
   2. [서버] 중복 확인 (이미 있으면 경고창)
   3. 신규이면 6자리 인증코드 생성 + 이메일 발송
   4. [팝업] 6자리 코드 입력
   5. 틀린 코드 → 에러 메시지 / 올바른 코드 → 구독 등록 완료
*/

const SUPABASE_URL = "https://fwptckxvhyzydrfralhw.supabase.co";
const SUPABASE_KEY = "sb_publishable_ZRdywELTvsTlfdU4SUCYsg_IASTgk3X";

// Cloudflare Pages Functions 엔드포인트 (배포 환경)
// 로컬에서도 wrangler pages dev 로 동일하게 동작합니다.
const API = {
    sendCode:   '/api/send-verify-code',
    verifyCode: '/api/verify-code'
};

// ─── 인증 팝업 삽입 ──────────────────────────────────────────
document.body.insertAdjacentHTML('beforeend', `
<div id="verify-overlay" style="
    display:none; position:fixed; inset:0;
    background:rgba(0,0,0,0.6); z-index:9999;
    justify-content:center; align-items:center;">
  <div style="
      background:#fff; border-radius:18px; padding:38px 32px 28px;
      max-width:360px; width:92%; box-shadow:0 24px 64px rgba(0,0,0,0.35);
      text-align:center; animation:fadeUp .25s ease;">
    <div style="font-size:2.4rem; margin-bottom:10px;">📬</div>
    <h3 style="margin:0 0 8px; color:#1a1a2e; font-size:1.15rem;">이메일 인증</h3>
    <p id="verify-email-label" style="font-size:.88rem; color:#555; margin-bottom:20px; word-break:break-all;"></p>
    <input id="verify-code-input" type="text" maxlength="6" placeholder="6자리 코드"
        inputmode="numeric" pattern="[0-9]*"
        style="width:100%; box-sizing:border-box; padding:14px; font-size:1.8rem;
               letter-spacing:10px; text-align:center; border:2px solid #dde3f0;
               border-radius:10px; outline:none; font-weight:800; color:#004e92;
               transition:border .2s;">
    <p id="verify-error" style="min-height:18px; font-size:.84rem; color:#e53e3e; margin:10px 0 0;"></p>
    <button id="verify-confirm-btn"
        style="width:100%; margin-top:14px; padding:13px; font-size:1rem; font-weight:700;
               background:linear-gradient(135deg,#004e92,#0077e6); color:#fff;
               border:none; border-radius:10px; cursor:pointer; transition:opacity .2s;">
        확인
    </button>
    <div style="margin-top:14px; font-size:.82rem; color:#999;">
        <button id="verify-resend-btn"
            style="background:none; border:none; color:#004e92; cursor:pointer;
                   font-size:.82rem; text-decoration:underline;">코드 재발송</button>
        &nbsp;·&nbsp;
        <button id="verify-cancel-btn"
            style="background:none; border:none; color:#aaa; cursor:pointer; font-size:.82rem;">취소</button>
    </div>
  </div>
</div>
<style>
@keyframes fadeUp {
  from { transform: translateY(20px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}
#verify-code-input:focus { border-color: #004e92; }
</style>
`);

// ─── 유틸 ────────────────────────────────────────────────────
function showOverlay() {
    document.getElementById('verify-overlay').style.display = 'flex';
    document.getElementById('verify-code-input').focus();
}
function hideOverlay() {
    document.getElementById('verify-overlay').style.display = 'none';
    document.getElementById('verify-code-input').value = '';
    document.getElementById('verify-error').innerText = '';
}
function setVerifyError(msg) {
    document.getElementById('verify-error').innerText = msg;
}

// 숫자만 입력 허용
document.getElementById('verify-code-input').addEventListener('input', e => {
    e.target.value = e.target.value.replace(/\D/g, '');
});

// ─────────────────────────────────────────────────────────────
// 1단계: 구독 버튼 클릭
// ─────────────────────────────────────────────────────────────
async function subscribe() {
    const emailInput = document.getElementById('email');
    const messageEl  = document.getElementById('message');
    const btn        = document.getElementById('btnText');
    const email      = (emailInput.value || '').trim().toLowerCase();

    // 기본 포맷 확인
    if (!email || !email.includes('@') || !email.includes('.')) {
        messageEl.innerHTML = '<span class="error">올바른 이메일 주소를 입력해 주세요.</span>';
        return;
    }

    btn.innerText = '처리 중...';
    btn.disabled  = true;
    messageEl.innerHTML = '<span style="color:#aaa;font-size:.88rem;">서버에 연결 중...</span>';

    try {
        const res = await fetch(API.sendCode, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const result = await res.json();

        if (result.duplicate) {
            // ─ 중복 이메일 경고창
            alert(`⚠️ 이미 등록된 이메일입니다!\n\n'${email}' 주소는 이미 구독 중입니다.\n다른 이메일 주소를 사용해 주세요.`);
            messageEl.innerHTML = '<span class="error">이미 등록된 이메일입니다.</span>';
            return;
        }

        if (!result.ok) {
            messageEl.innerHTML = `<span class="error">${result.error || '오류가 발생했습니다. 다시 시도해 주세요.'}</span>`;
            return;
        }

        // ─ 성공 → 팝업 열기
        messageEl.innerHTML = '<span style="color:#aaa;font-size:.88rem;">📧 인증 코드를 이메일로 발송했습니다.</span>';
        document.getElementById('verify-email-label').innerText =
            `${email}\n으로 발송된 6자리 인증 코드를 입력해 주세요.`;
        showOverlay();
        setupVerifyButtons(email);

    } catch (err) {
        console.error(err);
        messageEl.innerHTML = '<span class="error">서버 연결에 실패했습니다. 잠시 후 다시 시도해 주세요.</span>';
    } finally {
        btn.innerText = '무료 리포트 구독하기';
        btn.disabled  = false;
    }
}

// ─────────────────────────────────────────────────────────────
// 팝업 버튼 이벤트 연결
// ─────────────────────────────────────────────────────────────
function setupVerifyButtons(email) {
    // 확인 버튼
    document.getElementById('verify-confirm-btn').onclick = () => verifyAndRegister(email);
    // Enter 키
    document.getElementById('verify-code-input').onkeydown = e => {
        if (e.key === 'Enter') verifyAndRegister(email);
    };

    // 재발송 버튼
    document.getElementById('verify-resend-btn').onclick = async () => {
        setVerifyError('재발송 중...');
        try {
            const r = await fetch(API.sendCode, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const rj = await r.json();
            setVerifyError(rj.ok ? '✅ 재발송 완료! 이메일을 확인해 주세요.' : (rj.error || '재발송 실패'));
        } catch {
            setVerifyError('재발송 중 오류가 발생했습니다.');
        }
    };

    // 취소 버튼
    document.getElementById('verify-cancel-btn').onclick = () => {
        hideOverlay();
        document.getElementById('message').innerHTML = '';
    };
}

// ─────────────────────────────────────────────────────────────
// 2단계: 인증코드 검증 + 구독자 등록
// ─────────────────────────────────────────────────────────────
async function verifyAndRegister(email) {
    const codeInput = document.getElementById('verify-code-input');
    const confirmBtn = document.getElementById('verify-confirm-btn');
    const code = codeInput.value.trim();

    if (code.length !== 6) {
        setVerifyError('⚠️ 6자리 코드를 모두 입력해 주세요.');
        codeInput.focus();
        return;
    }

    confirmBtn.innerText = '확인 중...';
    confirmBtn.disabled  = true;
    setVerifyError('');

    try {
        const res = await fetch(API.verifyCode, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, code })
        });
        const result = await res.json();

        if (result.ok) {
            // ─ 인증 성공!
            hideOverlay();
            document.getElementById('message').innerHTML =
                '<span class="success">🎉 구독 완료! 내일 아침부터 리포트가 발송됩니다.</span>';
            document.getElementById('email').value = '';

        } else if (result.expired) {
            setVerifyError('⌛ 코드가 만료되었습니다. [코드 재발송] 버튼을 눌러주세요.');
        } else {
            // ─ 틀린 코드
            setVerifyError(`❌ ${result.error || '코드가 일치하지 않습니다. 다시 확인해 주세요.'}`);
            codeInput.value = '';
            codeInput.focus();
        }
    } catch (err) {
        console.error(err);
        setVerifyError('서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.');
    } finally {
        confirmBtn.innerText = '확인';
        confirmBtn.disabled  = false;
    }
}
