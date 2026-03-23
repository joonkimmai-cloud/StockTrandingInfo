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
    const r = await fetch(`${SUPABASE_URL}/rest/v1/${table}?${query}`, {
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

// ─── 데이터 로드 (AI 분석 그리드) ──────────────────────────────
async function loadNews() {
    const grid = document.getElementById('news-grid');
    if (!grid) return;

    // 감성 한글 매핑
    const sentimentMap = {
        'bullish': '📈 상승 우세',
        'bearish': '📉 하락 주의',
        'neutral': '⚖️ 중립'
    };
    const sentimentClass = {
        'bullish': 'positive',
        'bearish': 'negative',
        'neutral': 'neutral'
    };

    try {
        // stock_analysis 테이블에서 최신 AI 분석 데이터를 가져옴
        const query = "select=*,companies(name,symbol,per,pbr,marcap)&order=created_at.desc&limit=30";
        const allAnalysis = await sbGet('stock_analysis', query);

        if (!allAnalysis || allAnalysis.length === 0) {
            grid.innerHTML = '<div class="loading-state">현재 표시할 AI 분석 데이터가 없습니다.</div>';
            return;
        }

        // 중복 회사 제거 (가장 최신 분석만 선택)
        const uniqueCompanies = new Map();
        const filtered = [];
        
        for (const item of allAnalysis) {
            const compName = item.companies?.name || item.company_id;
            if (!uniqueCompanies.has(compName)) {
                uniqueCompanies.set(compName, true);
                filtered.push(item);
            }
            if (filtered.length === 6) break;
        }

        grid.innerHTML = '';

        for (const item of filtered) {
            const companyName = item.companies?.name || 'N/A';
            const symbol = item.companies?.symbol || '';
            const sent = (item.sentiment || 'neutral').toLowerCase();
            const sentLabel = sentimentMap[sent] || '⚖️ 중립';
            const sentCls = sentimentClass[sent] || 'neutral';
            
            // AI 분석 내용에서 처음 150자를 표시
            let summary = item.analysis_content || '분석 내용을 불러올 수 없습니다.';
            // Markdown 제거 (간단히)
            summary = summary.replace(/[#*_~`>\[\]]/g, '').replace(/\n+/g, ' ').trim();
            if (summary.length > 150) summary = summary.substring(0, 150) + '...';

            const date = new Date(item.created_at).toLocaleDateString('ko-KR', {
                year: 'numeric', month: 'short', day: 'numeric'
            });

            // 해당 회사의 최신 기사 ID를 찾아서 링크 연결
            const newsQuery = `company_id=eq.${item.company_id}&order=published_at.desc&limit=1&select=id`;
            const newsArticles = await sbGet('news_articles', newsQuery);
            const newsId = newsArticles && newsArticles.length > 0 ? newsArticles[0].id : null;
            const linkHref = newsId ? `news.html?id=${newsId}` : '#';

            const cardHtml = `
                <div class="card" onclick="location.href='${linkHref}'" style="cursor:pointer">
                    <div class="card-top-row">
                        <div class="company-name">${companyName} (${symbol})</div>
                        <span class="sentiment-badge ${sentCls}">${sentLabel}</span>
                    </div>
                    <div class="divider"></div>
                    <div class="summary">${summary}</div>
                    <div class="card-footer">
                        <div class="indicators">🤖 AI 분석</div>
                        <div class="post-date">${date}</div>
                    </div>
                </div>
            `;
            grid.insertAdjacentHTML('beforeend', cardHtml);
        }

    } catch (err) {
        console.error('loadNews error:', err);
        grid.innerHTML = '<div class="loading-state">데이터를 불러오는 중 오류가 발생했습니다.</div>';
    }
}

// ─── 인증코드 이메일 발송 (EmailJS) ─────────────────────────
async function sendCodeEmail(email, code) {
    if (typeof emailjs !== 'undefined') {
        return emailjs.send(EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, {
            to_email: email,
            verify_code: code,
            expiry_minutes: '10'
        }, EMAILJS_PUBLIC_KEY);
    }
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

    btn.innerText = 'Processing...';
    btn.disabled = true;
    messageEl.innerHTML = '';

    try {
        const existing = await sbGet('subscribers', `email=eq.${encodeURIComponent(email)}&select=email`);
        if (existing && existing.length > 0) {
            alert(`이미 구독 중인 이메일입니다.`);
            messageEl.innerHTML = '<span class="error">이미 등록된 이메일입니다.</span>';
            return;
        }

        showOverlay(email);
        bindVerifyButtons(email);
        
        const confirmBtn = document.getElementById('verify-confirm-btn');
        const codeInput = document.getElementById('verify-code-input');
        confirmBtn.disabled = true;
        codeInput.disabled = true;
        setErr('인증 코드를 발송하고 있습니다...');

        const code = String(Math.floor(100000 + Math.random() * 900000));
        const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString();

        await sbDelete('email_verifications', `email=eq.${encodeURIComponent(email)}`);
        await sbInsert('email_verifications', { email, code, expires_at: expiresAt, verified: false });
        await sendCodeEmail(email, code);
        
        setErr('');
        confirmBtn.disabled = false;
        codeInput.disabled = false;
        codeInput.focus();
        messageEl.innerHTML = '<span style="color:#aaa;font-size:.88rem;">📧 인증 코드가 발송되었습니다.</span>';

    } catch (err) {
        console.error('subscribe error:', err);
        hideOverlay();
        alert(`오류 발생: ${err.message}`);
    } finally {
        btn.innerText = 'Subscribe';
        btn.disabled = false;
    }
}

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
            setErr('✅ 재발송 완료!');
        } catch (e) { setErr(`실패: ${e.message}`); }
    };
    document.getElementById('verify-cancel-btn').onclick = () => hideOverlay();
}

async function verifyAndRegister(email) {
    const codeInput = document.getElementById('verify-code-input');
    const confirmBtn = document.getElementById('verify-confirm-btn');
    const code = codeInput.value.trim();
    if (code.length !== 6) { setErr('⚠️ 6자리 코드를 입력해 주세요.'); return; }
    confirmBtn.innerText = 'Wait...';
    confirmBtn.disabled = true;
    try {
        const records = await sbGet('email_verifications', `email=eq.${encodeURIComponent(email)}&select=*`);
        if (!records || records.length === 0) { setErr('인증 정보 없음'); return; }
        const rec = records[0];
        if (rec.expires_at < new Date().toISOString()) { setErr('⌛ 만료됨'); return; }
        if (rec.code !== code) { setErr('❌ 코드 틀림'); return; }
        await sbInsert('subscribers', { email }, 'resolution=merge-duplicates');
        await sbDelete('email_verifications', `email=eq.${encodeURIComponent(email)}`);
        hideOverlay();
        document.getElementById('message').innerHTML = '<span class="success">🎉 구독이 완료되었습니다!</span>';
        document.getElementById('email').value = '';
    } catch (err) { setErr(`오류: ${err.message}`); }
    finally { confirmBtn.innerText = 'Confirm'; confirmBtn.disabled = false; }
}

window.onload = loadNews;
