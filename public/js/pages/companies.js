import { renderPagination } from './pagination.js';

const PAGE_SIZE = 15;

export async function renderCompanies(contentEl, supabaseClient) {
    let currentPage = 0;

    // 1. 전체 건수 먼저 조회
    const { count } = await supabaseClient
        .from('companies')
        .select('*', { count: 'exact', head: true });

    const totalCount = count || 0;

    contentEl.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Collected Companies (수집된 주식 시장 회사들)</h1>
            <p class="page-desc">현재 우리 시스템이 예의주시하며 수집 중인 기업들의 목록 및 주요 수치입니다. (총 ${totalCount}개)</p>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th class="col-no">#</th>
                        <th style="width: 18%">종목코드 (Symbol)</th>
                        <th style="width: 28%">회사명 (Name)</th>
                        <th style="width: 28%">시가총액 (Marcap)</th>
                        <th style="width: 18%">PER / PBR</th>
                    </tr>
                </thead>
                <tbody id="list-body"></tbody>
            </table>
            <div id="pagination-container"></div>
        </div>
    `;

    async function loadPage(page) {
        currentPage = page;
        const from = page * PAGE_SIZE;
        const to = from + PAGE_SIZE - 1;

        const { data } = await supabaseClient
            .from('companies')
            .select('*')
            .order('updated_at', { ascending: false })
            .range(from, to);

        const tbody = document.getElementById('list-body');
        if (!tbody) return;

        if (data && data.length > 0) {
            tbody.innerHTML = data.map((row, i) => {
                const no = from + i + 1;
                const marcap = row.marcap ? (row.marcap / 100000000).toFixed(1) + '억 원' : '-';
                return `<tr>
                    <td class="col-no">${no}</td>
                    <td><b>${row.symbol}</b></td>
                    <td>${row.name}</td>
                    <td style="color:var(--primary-blue)">${marcap}</td>
                    <td>${row.per || '-'}/${row.pbr || '-'}</td>
                </tr>`;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px;">수집된 데이터가 없습니다.</td></tr>';
        }

        renderPagination('pagination-container', currentPage, totalCount, PAGE_SIZE, loadPage);
    }

    await loadPage(0);
}
