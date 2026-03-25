/**
 * Cloudflare Pages Function: /api/send-verify-code
 * 역할: 중복 이메일 확인 후 6자리 인증코드 생성 → Supabase 저장 → Resend로 이메일 발송
 *
 * 필요한 Cloudflare 환경변수 (Dashboard > Settings > Environment variables):
 *   SUPABASE_URL, SUPABASE_KEY, RESEND_API_KEY
 */
export async function onRequestPost(context) {
    const { env, request } = context;

    // CORS 헤더
    const corsHeaders = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    };

    if (request.method === 'OPTIONS') {
        return new Response(null, { headers: corsHeaders });
    }

    try {
        const { email } = await request.json();
        if (!email || !email.includes('@')) {
            return new Response(JSON.stringify({ ok: false, error: '유효하지 않은 이메일 형식입니다.' }), { headers: corsHeaders });
        }

        const supabaseUrl = env.SUPABASE_URL;
        const supabaseKey = env.SUPABASE_KEY;
        const resendApiKey = env.RESEND_API_KEY;
        const sbHeaders = {
            'apikey': supabaseKey,
            'Authorization': `Bearer ${supabaseKey}`,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        };

        // ① 중복 이메일 확인
        const checkResp = await fetch(`${supabaseUrl}/rest/v1/subscribers?email=eq.${encodeURIComponent(email)}&select=email`, { headers: sbHeaders });
        const existing = await checkResp.json();
        if (existing && existing.length > 0) {
            return new Response(JSON.stringify({ ok: false, duplicate: true, error: `'${email}' 주소는 이미 등록된 이메일입니다.` }), { headers: corsHeaders });
        }

        // ② 6자리 인증코드 생성 + 만료 10분
        const code = String(Math.floor(100000 + Math.random() * 900000));
        const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString();

        // ③ 기존 코드 삭제 후 새 코드 저장
        await fetch(`${supabaseUrl}/rest/v1/email_verifications?email=eq.${encodeURIComponent(email)}`, { method: 'DELETE', headers: sbHeaders });
        await fetch(`${supabaseUrl}/rest/v1/email_verifications`, {
            method: 'POST', headers: sbHeaders,
            body: JSON.stringify({ email, code, expires_at: expiresAt, verified: false })
        });

        // ④ Resend API로 인증 이메일 발송
        const htmlBody = `
        <div style="font-family:'Segoe UI',sans-serif;background:#f0f2f5;padding:40px 20px;">
          <div style="max-width:460px;margin:0 auto;background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 6px 24px rgba(0,0,0,.12);">
            <div style="background:linear-gradient(135deg,#004e92,#000428);color:#fff;padding:32px;text-align:center;">
              <h2 style="margin:0;font-size:1.4rem;">📬 이메일 인증</h2>
              <p style="margin:8px 0 0;opacity:.8;font-size:.9rem;">short game 구독 인증 코드입니다.</p>
            </div>
            <div style="padding:36px;text-align:center;">
              <p style="font-size:1rem;color:#333;margin-bottom:6px;">아래 6자리 인증 코드를 입력해 주세요.</p>
              <div style="font-size:44px;font-weight:800;letter-spacing:14px;color:#004e92;
                          background:#eef3ff;border-radius:12px;padding:20px 24px;margin:20px 0;
                          display:inline-block;">${code}</div>
              <p style="font-size:.85rem;color:#888;">이 코드는 <b>10분</b> 동안만 유효합니다.</p>
              <p style="font-size:.78rem;color:#bbb;margin-top:24px;">본인이 요청하지 않은 경우 이 메일을 무시하세요.</p>
            </div>
          </div>
        </div>`;

        const emailResp = await fetch('https://api.resend.com/emails', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${resendApiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                from: 'short game <onboarding@resend.dev>',
                to: [email],
                subject: '[short game] 이메일 인증 코드',
                html: htmlBody
            })
        });

        if (!emailResp.ok) {
            const errText = await emailResp.text();
            console.error('Resend error:', errText);
            return new Response(JSON.stringify({ ok: false, error: '이메일 발송에 실패했습니다. 관리자에게 문의해 주세요.' }), { headers: corsHeaders });
        }

        return new Response(JSON.stringify({ ok: true, message: '인증 코드가 발송되었습니다.' }), { headers: corsHeaders });

    } catch (e) {
        console.error('send-verify-code error:', e);
        return new Response(JSON.stringify({ ok: false, error: `서버 오류: ${e.message}` }), { status: 500, headers: corsHeaders });
    }
}

// OPTIONS preflight 처리
export async function onRequestOptions() {
    return new Response(null, {
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
    });
}
