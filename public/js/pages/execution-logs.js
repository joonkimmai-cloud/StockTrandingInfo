import { renderPagination } from './pagination.js';

const PAGE_SIZE = 15;

export async function renderExecutionLogs(contentEl, supabaseClient) {
    let currentPage = 0;
    let currentQuery = '';

    contentEl.innerHTML = `
        <div class="page-header" style="display:flex; justify-content:space-between; align-items:flex-end;">
            <div>
                <h1 class="page-title">Execution Logs</h1>
                <p class="page-desc" id="logs-count-text">자동 작업 단계별 기록입니다.</p>
            </div>
            <div class="page-header-actions">
                <div class="search-container">
                    <input type="text" id="logs-search-input" class="search-input" placeholder="단계명, 상태, 메시지 검색...">
                    <button id="logs-search-btn" class="search-btn">🔍</button>
                </div>
            </div>
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

    async function loadPage(page, query = currentQuery) {
        currentPage = page;
        currentQuery = query;
        const from = page * PAGE_SIZE;
        const to = from + PAGE_SIZE - 1;

        const tbody = document.getElementById('list-body');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px;">불러오는 중...</td></tr>';

        let q = supabaseClient.from('execution_logs').select('*', { count: 'exact' });
        
        if (query) {
            q = q.or(`step_name.ilike.*${query}*,status.ilike.*${query}*,log_message.ilike.*${query}*`);
        }

        const { data, count, error } = await q
            .order('created_at', { ascending: false })
            .range(from, to);

        if (error) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:30px; color:red;">에러: ${error.message}</td></tr>`;
            return;
        }

        const totalCount = count || 0;
        document.getElementById('logs-count-text').innerText = `자동 작업 단계별 기록입니다. (총 ${totalCount}개${query ? ' 검색됨' : ''})`;

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

        renderPagination('pagination-container', currentPage, totalCount, PAGE_SIZE, (p) => loadPage(p, currentQuery));
    }

    // 검색 이벤트 바인딩
    const searchInput = document.getElementById('logs-search-input');
    const searchBtn = document.getElementById('logs-search-btn');

    const handleSearch = () => {
        loadPage(0, searchInput.value.trim());
    };

    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });

    await loadPage(0);
}
