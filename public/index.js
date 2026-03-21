/*
   index.js v3
   이메일 구독 플로우 (완전 클라이언트사이드):
   1. 이메일 입력 → 구독 버튼 클릭
   2. Supabase에서 중복 확인 → 이미 있으면 경고창
   3. 6자리 코드 생성 → Supabase email_verifications 테이블에 저장
   4. EmailJS로 인증 코드 이메일 발송
   5. 팝업에서 코드 입력 → Supabase에서 검증
   6. 성공 → subscribers 테이블에 등록
*/

// ─── Supabase 설정 ────────────────────────────────────────────
const SUPABASE_URL = "https://fwptckxvhyzydrfralhw.supabase.co";
const SUPABASE_KEY = "sb_publishable_ZRdywELTvsTlfdU4SUCYsg_IASTgk3X";
let sb;
try { sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY); } catch (e) { }

// ─── EmailJS 설정 ─────────────────────────────────────────────
// emailjs.com 에서 무료 계정 생성 후 아래 값을 설정해주세요.
const EMAILJS_SERVICE_ID = "service_stockalpha";   // EmailJS 대시보드 > Email Services
const EMAILJS_TEMPLATE_ID = "template_verify";      // EmailJS 대시보드 > Email Templates
const EMAILJS_PUBLIC_KEY = "5pIFRIOsofsS22DQ4"; // EmailJS 대시보드 > Account > Public Key

// ─── 팝업 HTML 주입 ──────────────────────────────────────────
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
    <p id="verify-email-label" style="font-size:.88rem; color:#555; margin-bottom:20px;"></p>
    <input id="verify-code-input" type="text" maxlength="6" placeholder="6자리 코드"
        inputmode="numeric"
        style="width:100%; box-sizing:border-box; padding:14px; font-size:1.8rem;
               letter-spacing:10px; text-align:center; border:2px solid #dde3f0;
               border-radius:10px; outline:none; font-weight:800; color:#004e92;">
    <p id="verify-error" style="min-height:20px; font-size:.84rem; color:#e53e3e; margin:10px 0 0;"></p>
    <button id="verify-confirm-btn"
        style="width:100%; margin-top:14px; padding:13px; font-size:1rem; font-weight:700;
               background:linear-gradient(135deg,#004e92,#0077e6); color:#fff;
               border:none; border-radius:10px; cursor:pointer;">확인</button>
    <div style="margin-top:14px; font-size:.82rem; color:#999;">
        <button id="verify-resend-btn" style="background:none;border:none;color:#004e92;cursor:pointer;font-size:.82rem;text-decoration:underline;">코드 재발송</button>
        &nbsp;·&nbsp;
        <button id="verify-cancel-btn" style="background:none;border:none;color:#aaa;cursor:pointer;font-size:.82rem;">취소</button>
    </div>
  </div>
</div>
<style>
@keyframes fadeUp { from{transform:translateY(20px);opacity:0} to{transform:translateY(0);opacity:1} }
#verify-code-input:focus { border-color: #004e92; }
</style>
`);

// 숫자만 입력
document.getElementById('verify-code-input').addEventListener('input', e => {
    e.target.value = e.target.value.replace(/\D/g, '');
});

function showOverlay(email) {
    document.getElementById('verify-email-label').innerText = `${email}\n위 주소로 발송된 6자리 인증 코드를 입력하세요.`;
    document.getElementById('verify-code-input').value = '';
    document.getElementById('verify-error').innerText = '';
    document.getElementById('verify-overlay').style.display = 'flex';
    setTimeout(() => document.getElementById('verify-code-input').focus(), 100);
}
function hideOverlay() {
    document.getElementById('verify-overlay').style.display = 'none';
}
function setErr(msg) { document.getElementById('verify-error').innerText = msg; }

// ─── Supabase 헬퍼 (REST 직접 호출) ─────────────────────────
async function sbGet(table, query) {
    const r = await fetch(`${SUPABASE_URL}/rest/v1/${table}?${query}&select=*`, {
        headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` }
    });
    return r.json();
}
async function sbInsert(table, payload, prefer = 'return=minimal') {
    return fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
        method: 'POST',
        headers: {
            apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`,
            'Content-Type': 'application/json', Prefer: prefer
        },
        body: JSON.stringify(payload)
    });
}
async function sbDelete(table, query) {
    return fetch(`${SUPABASE_URL}/rest/v1/${table}?${query}`, {
        method: 'DELETE',
        headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` }
    });
}

// ─── 인증코드 이메일 발송 (EmailJS) ─────────────────────────
async function sendCodeEmail(email, code) {
    // EmailJS SDK가 로드된 경우 사용
    if (typeof emailjs !== 'undefined') {
        return emailjs.send(EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, {
            to_email: email,
            verify_code: code,
            expiry_minutes: '10'
        }, EMAILJS_PUBLIC_KEY);
    }
    // fallback: Cloudflare Pages Function 시도
    const res = await fetch('/api/send-verify-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code })
    });
    if (!res.ok) throw new Error('이메일 발송 서비스에 연결할 수 없습니다.');
    const json = await res.json();
    if (!json.ok) throw new Error(json.error);
}

// ─────────────────────────────────────────────────────────────
// 1단계: 구독 버튼 클릭
// ─────────────────────────────────────────────────────────────
async function subscribe() {
    const emailInput = document.getElementById('email');
    const messageEl = document.getElementById('message');
    const btn = document.getElementById('btnText');
    const email = (emailInput.value || '').trim().toLowerCase();

    if (!email || !email.includes('@') || !email.includes('.')) {
        messageEl.innerHTML = '<span class="error">올바른 이메일 주소를 입력해 주세요.</span>';
        return;
    }

    btn.innerText = '처리 중...';
    btn.disabled = true;
    messageEl.innerHTML = '';

    try {
        // ① 중복 확인
        const existing = await sbGet('subscribers', `email=eq.${encodeURIComponent(email)}`);
        if (existing && existing.length > 0) {
            alert(`⚠️ 이미 등록된 이메일입니다!\n\n'${email}' 주소는 이미 구독 중입니다.\n다른 이메일 주소를 사용해 주세요.`);
            messageEl.innerHTML = '<span class="error">이미 등록된 이메일입니다.</span>';
            return;
        }

        // ② 팝업을 먼저 띄움 (이메일 발송 성공/실패와 무관하게 표시)
        showOverlay(email);
        bindVerifyButtons(email);
        messageEl.innerHTML = '<span style="color:#aaa;font-size:.88rem;">📧 인증 코드를 발송 중입니다...</span>';
        setErr('코드 발송 중... 잠시만 기다려 주세요.');

        // ③ 6자리 코드 생성
        const code = String(Math.floor(100000 + Math.random() * 900000));
        const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString();

        // ④ Supabase에 코드 저장
        await sbDelete('email_verifications', `email=eq.${encodeURIComponent(email)}`);
        const saveResp = await sbInsert('email_verifications', { email, code, expires_at: expiresAt, verified: false });
        if (!saveResp.ok && saveResp.status !== 201) {
            const errBody = await saveResp.text().catch(() => '');
            console.error('DB save failed:', saveResp.status, errBody);
            setErr(`⚠️ DB 저장 오류(${saveResp.status}): email_verifications 테이블이 Supabase에 생성되어 있는지 확인해 주세요.`);
            return;
        }

        // ⑤ 이메일 발송
        try {
            await sendCodeEmail(email, code);
            setErr('');
            messageEl.innerHTML = '<span style="color:#aaa;font-size:.88rem;">📧 이메일을 확인하여 코드를 입력해 주세요.</span>';
        } catch (emailErr) {
            console.error('Email send failed:', emailErr);
            setErr(`⚠️ 이메일 발송 실패: ${emailErr.message || emailErr}\n코드를 직접 콘솔에서 확인하거나 재발송을 눌러주세요.`);
            // 이메일 발송 실패해도 팝업은 유지 (재발송 버튼으로 재시도 가능)
        }

    } catch (err) {
        console.error('subscribe error:', err);
        messageEl.innerHTML = `<span class="error">오류: ${err.message}</span>`;
    } finally {
        btn.innerText = '무료 리포트 구독하기';
        btn.disabled = false;
    }

}

// ─────────────────────────────────────────────────────────────
// 팝업 버튼 이벤트
// ─────────────────────────────────────────────────────────────
function bindVerifyButtons(email) {
    document.getElementById('verify-confirm-btn').onclick = () => verifyAndRegister(email);
    document.getElementById('verify-code-input').onkeydown = e => { if (e.key === 'Enter') verifyAndRegister(email); };

    document.getElementById('verify-resend-btn').onclick = async () => {
        setErr('재발송 중...');
        try {
            const code = String(Math.floor(100000 + Math.random() * 900000));
            const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString();
            await sbDelete('email_verifications', `email=eq.${encodeURIComponent(email)}`);
            await sbInsert('email_verifications', { email, code, expires_at: expiresAt, verified: false });
            await sendCodeEmail(email, code);
            setErr('✅ 재발송 완료! 이메일을 확인해 주세요.');
        } catch (e) { setErr(`재발송 실패: ${e.message}`); }
    };

    document.getElementById('verify-cancel-btn').onclick = () => {
        hideOverlay();
        document.getElementById('message').innerHTML = '';
    };
}

// ─────────────────────────────────────────────────────────────
// 2단계: 코드 검증 + 구독 등록
// ─────────────────────────────────────────────────────────────
async function verifyAndRegister(email) {
    const codeInput = document.getElementById('verify-code-input');
    const confirmBtn = document.getElementById('verify-confirm-btn');
    const code = codeInput.value.trim();

    if (code.length !== 6) { setErr('⚠️ 6자리 코드를 모두 입력해 주세요.'); codeInput.focus(); return; }

    confirmBtn.innerText = '확인 중...';
    confirmBtn.disabled = true;
    setErr('');

    try {
        // ① Supabase에서 코드 조회
        const records = await sbGet('email_verifications', `email=eq.${encodeURIComponent(email)}`);

        if (!records || records.length === 0) {
            setErr('인증 요청 정보가 없습니다. 처음부터 다시 시도해 주세요.');
            return;
        }
        const rec = records[0];
        const now = new Date().toISOString();

        // ② 만료 확인
        if (rec.expires_at < now) {
            setErr('⌛ 코드가 만료되었습니다. [코드 재발송]을 눌러주세요.');
            return;
        }

        // ③ 코드 일치 확인
        if (rec.code !== code) {
            setErr('❌ 인증 코드가 일치하지 않습니다. 다시 확인해 주세요.');
            codeInput.value = '';
            codeInput.focus();
            return;
        }

        // ④ 성공 → subscribers 등록
        const regResp = await sbInsert('subscribers', { email }, 'resolution=merge-duplicates');
        if (!regResp.ok && regResp.status !== 201) {
            throw new Error('구독자 등록에 실패했습니다.');
        }

        // ⑤ 인증 레코드 삭제
        await sbDelete('email_verifications', `email=eq.${encodeURIComponent(email)}`);

        hideOverlay();
        document.getElementById('message').innerHTML = '<span class="success">🎉 구독 완료! 내일 아침부터 리포트가 발송됩니다.</span>';
        document.getElementById('email').value = '';

    } catch (err) {
        console.error('verify error:', err);
        setErr(`오류: ${err.message}`);
    } finally {
        confirmBtn.innerText = '확인';
        confirmBtn.disabled = false;
    }
}
