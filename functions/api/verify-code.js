/**
 * Cloudflare Pages Function: /api/verify-code
 * 역할: 인증코드 검증 → 성공 시 subscribers 등록
 *
 * 필요 환경변수: SUPABASE_URL, SUPABASE_KEY
 */
export async function onRequestPost(context) {
    const { env, request } = context;

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
        const { email, code } = await request.json();

        if (!email || !code) {
            return new Response(JSON.stringify({ ok: false, error: '이메일 또는 코드가 누락되었습니다.' }), { headers: corsHeaders });
        }

        const supabaseUrl = env.SUPABASE_URL;
        const supabaseKey = env.SUPABASE_KEY;
        const sbHeaders = {
            'apikey': supabaseKey,
            'Authorization': `Bearer ${supabaseKey}`,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        };

        // ① Supabase에서 인증 레코드 조회
        const resp = await fetch(
            `${supabaseUrl}/rest/v1/email_verifications?email=eq.${encodeURIComponent(email)}&select=code,expires_at`,
            { headers: sbHeaders }
        );
        const records = await resp.json();

        if (!records || records.length === 0) {
            return new Response(JSON.stringify({ ok: false, error: '인증 요청 정보가 없습니다. 처음부터 다시 시도해 주세요.' }), { headers: corsHeaders });
        }

        const record = records[0];
        const now = new Date().toISOString();

        // ② 만료 확인
        if (record.expires_at < now) {
            return new Response(JSON.stringify({ ok: false, expired: true, error: '인증 코드가 만료되었습니다. 코드를 재발송해 주세요.' }), { headers: corsHeaders });
        }

        // ③ 코드 일치 확인
        if (record.code !== String(code).trim()) {
            return new Response(JSON.stringify({ ok: false, error: '인증 코드가 일치하지 않습니다. 다시 확인해 주세요.' }), { headers: corsHeaders });
        }

        // ④ 인증 성공 → subscribers 등록
        await fetch(
            `${supabaseUrl}/rest/v1/subscribers?on_conflict=email`,
            {
                method: 'POST',
                headers: { ...sbHeaders, 'Prefer': 'resolution=merge-duplicates' },
                body: JSON.stringify({ email })
            }
        );

        // ⑤ 사용된 인증 레코드 삭제
        await fetch(
            `${supabaseUrl}/rest/v1/email_verifications?email=eq.${encodeURIComponent(email)}`,
            { method: 'DELETE', headers: sbHeaders }
        );

        return new Response(JSON.stringify({ ok: true, message: '인증 완료! 구독이 등록되었습니다.' }), { headers: corsHeaders });

    } catch (e) {
        console.error('verify-code error:', e);
        return new Response(JSON.stringify({ ok: false, error: `서버 오류: ${e.message}` }), { status: 500, headers: corsHeaders });
    }
}
