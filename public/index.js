/* 
   index.js
   이메일 구독 로직 (중복 확인 → 인증코드 발송 → 입력 검증 → 등록)
*/

const SUPABASE_URL = "https://fwptckxvhyzydrfralhw.supabase.co";
const SUPABASE_KEY = "sb_publishable_ZRdywELTvsTlfdU4SUCYsg_IASTgk3X";
// Flask API 서버 (이메일 발송은 서버 사이드에서 처리)
const API_BASE = "http://localhost:5000";

let supabaseClient;
try {
    supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
} catch (e) {
    console.error("Supabase 초기화 오류:", e);
}

// ─── 인증 팝업 HTML을 body에 주입 ───────────────────────────────
const verifyModalHTML = `
<div id="verify-overlay" style="
    display:none; position:fixed; inset:0;
    background:rgba(0,0,0,0.55); z-index:9999;
    justify-content:center; align-items:center;">
    <div style="
        background:#fff; border-radius:16px; padding:36px 32px;
        max-width:380px; width:90%; box-shadow:0 20px 60px rgba(0,0,0,0.3);
        text-align:center;">
        <div style="font-size:2.2rem; margin-bottom:8px;">📬</div>
        <h3 style="margin:0 0 6px; font-size:1.2rem; color:#1a1a2e;">이메일 인증</h3>
        <p id="verify-desc" style="font-size:0.9rem; color:#666; margin-bottom:22px;"></p>
        <input id="verify-code-input" type="text" maxlength="6" placeholder="6자리 인증 코드"
            style="width:100%; box-sizing:border-box; padding:14px 16px; font-size:1.5rem;
                   letter-spacing:8px; text-align:center; border:2px solid #ddd;
                   border-radius:10px; outline:none; font-weight:700; color:#004e92;">
        <div id="verify-error" style="color:#e53e3e; font-size:0.85rem; min-height:20px; margin:10px 0 4px;"></div>
        <button id="verify-confirm-btn" style="
            width:100%; padding:13px; background:linear-gradient(135deg,#004e92,#0077e6);
            color:#fff; border:none; border-radius:10px; font-size:1rem;
            font-weight:700; cursor:pointer; margin-top:4px;">확인</button>
        <br>
        <button id="verify-resend-btn" style="
            margin-top:10px; background:none; border:none; color:#888;
            font-size:0.82rem; cursor:pointer; text-decoration:underline;">
            코드 재발송
        </button>
        <button id="verify-cancel-btn" style="
            margin-top:4px; margin-left:12px; background:none; border:none;
            color:#aaa; font-size:0.82rem; cursor:pointer;">취소</button>
    </div>
</div>
`;
document.body.insertAdjacentHTML('beforeend', verifyModalHTML);

// 팝업 열기/닫기
function openVerifyModal(email) {
    const overlay = document.getElementById('verify-overlay');
    document.getElementById('verify-desc').innerText = `${email} 으로 인증 코드를 발송했습니다.\n이메일을 확인하고 6자리 코드를 입력해 주세요.`;
    document.getElementById('verify-code-input').value = '';
    document.getElementById('verify-error').innerText = '';
    overlay.style.display = 'flex';
    document.getElementById('verify-code-input').focus();
}
function closeVerifyModal() {
    document.getElementById('verify-overlay').style.display = 'none';
}

// 코드 입력 시 숫자만 & 자동 완성 포커스 이동
document.getElementById('verify-code-input').addEventListener('input', (e) => {
    e.target.value = e.target.value.replace(/\D/g, '');
});

// ─────────────────────────────────────────────────────────────
// 1단계: 구독 버튼 클릭 → 중복 확인 + 인증코드 발송
// ─────────────────────────────────────────────────────────────
async function subscribe() {
    const emailInput = document.getElementById('email');
    const messageEl = document.getElementById('message');
    const btn = document.getElementById('btnText');
    const email = (emailInput.value || '').trim();

    if (!email || !email.includes('@')) {
        messageEl.innerHTML = '<span class="error">올바른 이메일 주소가 아닙니다.</span>';
        return;
    }

    btn.innerText = '처리 중...';
    btn.disabled = true;
    messageEl.innerHTML = '';

    try {
        const res = await fetch(`${API_BASE}/send-verify-code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const result = await res.json();

        if (!result.ok && result.duplicate) {
            // 중복 이메일 경고
            alert(`⚠️ '${email}' 주소는 이미 등록된 이메일입니다.\n다른 이메일을 사용해 주세요.`);
            messageEl.innerHTML = '<span class="error">이미 구독 중인 이메일입니다.</span>';
            return;
        }

        if (!result.ok) {
            messageEl.innerHTML = `<span class="error">${result.error || '오류가 발생했습니다.'}</span>`;
            return;
        }

        // 성공 → 인증 팝업 열기
        messageEl.innerHTML = '<span style="color:#aaa; font-size:0.88rem;">인증 코드를 이메일로 발송했습니다.</span>';
        openVerifyModal(email);

        // 확인 버튼 이벤트
        const confirmBtn = document.getElementById('verify-confirm-btn');
        confirmBtn.onclick = () => verifyAndRegister(email);

        // 재발송 버튼 이벤트
        document.getElementById('verify-resend-btn').onclick = async () => {
            document.getElementById('verify-error').innerText = '재발송 중...';
            const r2 = await fetch(`${API_BASE}/send-verify-code`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const r2j = await r2.json();
            document.getElementById('verify-error').innerText = r2j.ok ? '✅ 재발송 완료!' : r2j.error;
        };

        // 취소 버튼
        document.getElementById('verify-cancel-btn').onclick = () => {
            closeVerifyModal();
            messageEl.innerHTML = '';
        };

        // Enter키로 확인
        document.getElementById('verify-code-input').onkeydown = (e) => {
            if (e.key === 'Enter') verifyAndRegister(email);
        };

    } catch (err) {
        console.error(err);
        messageEl.innerHTML = '<span class="error">서버 연결에 실패했습니다. 잠시 후 다시 시도해 주세요.</span>';
    } finally {
        btn.innerText = '무료 리포트 구독하기';
        btn.disabled = false;
    }
}

// ─────────────────────────────────────────────────────────────
// 2단계: 인증코드 확인 → 구독자 등록
// ─────────────────────────────────────────────────────────────
async function verifyAndRegister(email) {
    const codeInput = document.getElementById('verify-code-input');
    const errorEl = document.getElementById('verify-error');
    const confirmBtn = document.getElementById('verify-confirm-btn');
    const code = codeInput.value.trim();

    if (code.length !== 6) {
        errorEl.innerText = '⚠️ 6자리 코드를 입력해 주세요.';
        codeInput.focus();
        return;
    }

    confirmBtn.innerText = '확인 중...';
    confirmBtn.disabled = true;
    errorEl.innerText = '';

    try {
        const res = await fetch(`${API_BASE}/verify-code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, code })
        });
        const result = await res.json();

        if (result.ok) {
            // 성공!
            closeVerifyModal();
            document.getElementById('message').innerHTML =
                '<span class="success">🎉 구독 완료! 내일 아침부터 리포트가 발송됩니다.</span>';
            document.getElementById('email').value = '';
        } else if (result.expired) {
            errorEl.innerText = '⌛ 코드가 만료되었습니다. 재발송 버튼을 눌러주세요.';
        } else {
            errorEl.innerText = `❌ ${result.error || '인증 코드가 올바르지 않습니다.'}`;
            codeInput.value = '';
            codeInput.focus();
        }
    } catch (err) {
        console.error(err);
        errorEl.innerText = '서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';
    } finally {
        confirmBtn.innerText = '확인';
        confirmBtn.disabled = false;
    }
}
