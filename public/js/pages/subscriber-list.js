// ==========================================
// 뉴스레터를 구독하는 '구독자 명단' 페이지
// ==========================================
export async function renderSubscriberList(contentEl, supabaseClient) {
    // 1. Supabase 데이터베이스에서 최신순으로(생성된 날짜 기준) 구독자 전체 목록을 불러옵니다.
    const { data } = await supabaseClient
        .from('subscribers')
        .select('*')
        .order('created_at', { ascending: false });

    // 2. 관리자 화면(웹 페이지)에 데이터를 그립니다.
    contentEl.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Subscribers (구독자 관리)</h1>
            <p class="page-desc">아침 6시 주식 뉴스레터를 받는 사람들의 정보입니다.</p>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th style="width: 40%">이메일 주소 (Email Address)</th>
                        <th style="width: 30%">구독 상태 (Status)</th>
                        <th style="width: 30%">가입 날짜 (Joined Date)</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- 사람마다 한 줄(tr)씩 반복(map)해서 그려줌 -->
                    ${data?.map(row => `
                        <tr>
                            <!-- 진하게 이메일 표시 -->
                            <td style="font-weight:600">${row.email}</td>
                            <!-- 현재 사용 중이라는 표시 -->
                            <td>Active (활성)</td>
                            <!-- 글자색 흐리게(회색) 가입 날짜 표시 -->
                            <td style="color:var(--text-muted)">
                                ${new Date(row.created_at).toLocaleDateString('ko-KR', { timeZone: 'Asia/Seoul' })}
                            </td>
                        </tr>
                    `).join('') || '<tr><td colspan="3">현재 구독자가 없습니다.</td></tr>'}
                </tbody>
            </table>
        </div>
    `;
}
