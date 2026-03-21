import { renderPagination } from './pagination.js';

const PAGE_SIZE = 15;

export async function renderExecutionLogs(contentEl, supabaseClient) {
    let currentPage = 0;

    const { count } = await supabaseClient
        .from('execution_logs')
        .select('*', { count: 'exact', head: true });

    const totalCount = count || 0;

    contentEl.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Execution Logs (실행 로그 관리)</h1>
            <p class="page-desc">자동 작업(Batch)이 진행되는 과정에서의 주요 단계별 기록(로그)을 확인할 수 있습니다. (총 ${totalCount}개)</p>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th class="col-no">#</th>
                        <th style="width: 15%">발생 시간 (Time)</th>
                        <th style="width: 20%">진행 단계 (Step)</th>
                        <th style="width: 13%">상태 (Status)</th>
                        <th>상세 메시지 (Message)</th>
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
            .from('execution_logs')
            .select('*')
            .order('created_at', { ascending: false })
            .range(from, to);

        const tbody = document.getElementById('list-body');
        if (!tbody) return;

        if (data && data.length > 0) {
            tbody.innerHTML = data.map((row, i) => {
                const no = from + i + 1;
                const dateText = new Date(row.created_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
                const statusClass = (row.status || '').toLowerCase();
                return `<tr>
                    <td class="col-no">${no}</td>
                    <td style="color:var(--text-muted); font-size:0.8rem;">${dateText}</td>
                    <td style="font-weight:600">${row.step_name}</td>
                    <td><span class="status-dot ${statusClass}"></span>${row.status}</td>
                    <td style="font-size:0.85rem">${row.log_message || ''}</td>
                </tr>`;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px;">No logs available (로그가 없습니다.)</td></tr>';
        }

        renderPagination('pagination-container', currentPage, totalCount, PAGE_SIZE, loadPage);
    }

    await loadPage(0);
}
