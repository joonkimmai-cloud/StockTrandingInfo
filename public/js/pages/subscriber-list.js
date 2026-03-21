import { renderPagination } from './pagination.js';

const PAGE_SIZE = 15;

export async function renderSubscriberList(contentEl, supabaseClient) {
    let currentPage = 0;

    const { count } = await supabaseClient
        .from('subscribers')
        .select('*', { count: 'exact', head: true });

    const totalCount = count || 0;

    contentEl.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Subscribers (구독자 관리)</h1>
            <p class="page-desc">아침 6시 주식 뉴스레터를 받는 사람들의 정보입니다. (총 ${totalCount}명)</p>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th class="col-no">#</th>
                        <th style="width: 42%">이메일 주소 (Email Address)</th>
                        <th style="width: 28%">구독 상태 (Status)</th>
                        <th style="width: 25%">가입 날짜 (Joined Date)</th>
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
            .from('subscribers')
            .select('*')
            .order('created_at', { ascending: false })
            .range(from, to);

        const tbody = document.getElementById('list-body');
        if (!tbody) return;

        if (data && data.length > 0) {
            tbody.innerHTML = data.map((row, i) => {
                const no = from + i + 1;
                const dateText = new Date(row.created_at).toLocaleDateString('ko-KR', { timeZone: 'Asia/Seoul' });
                return `<tr>
                    <td class="col-no">${no}</td>
                    <td style="font-weight:600">${row.email}</td>
                    <td>Active (활성)</td>
                    <td style="color:var(--text-muted)">${dateText}</td>
                </tr>`;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:30px;">현재 구독자가 없습니다.</td></tr>';
        }

        renderPagination('pagination-container', currentPage, totalCount, PAGE_SIZE, loadPage);
    }

    await loadPage(0);
}
