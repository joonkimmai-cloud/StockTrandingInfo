// ==========================================
// 시가총액 상위로 수집된 '기업(회사)' 목록 페이지
// ==========================================
export async function renderCompanies(contentEl, supabaseClient) {
    // 1. Supabase(데이터베이스)에서 주식 회사 정보를 시가총액(marcap) 기준 내림차순(가장 큰 순서)으로 가져옵니다.
    const { data } = await supabaseClient
        .from('companies')
        .select('*')
        .order('marcap', { ascending: false });

    // 2. 화면(HTML) 구성
    contentEl.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Collected Companies (수집된 주식 시장 회사들)</h1>
            <p class="page-desc">현재 우리 시스템이 예의주시하며 수집 중인 기업들의 목록 및 주요 수치입니다.</p>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th style="width: 20%">종목코드 (Symbol)</th>
                        <th style="width: 30%">회사명 (Name)</th>
                        <th style="width: 30%">시가총액 (Marcap)</th>
                        <th style="width: 20%">PER / PBR</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- map 함수를 이용해 여러 회사를 그려줍니다 -->
                    ${data?.map(row => `
                        <tr>
                            <td><b>${row.symbol}</b></td>
                            <!-- 회사명 -->
                            <td>${row.name}</td>
                            <!-- 파란색 글씨로 시가총액 표시. (단위를 줄여서 '억' 으로 표시) -->
                            <td style="color:var(--primary-blue)">
                                ${row.marcap ? (row.marcap / 100000000).toFixed(1) + '억 원' : '-'}
                            </td>
                            <!-- 주식 평가 지표인 PER / PBR -->
                            <td>${row.per || '-'}/${row.pbr || '-'}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="4">수집된 데이터가 없습니다.</td></tr>'}
                </tbody>
            </table>
        </div>
    `;
}
