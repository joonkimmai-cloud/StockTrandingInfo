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

        const { data, error } = await supabaseClient
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
                const statusLabel = row.is_active !== false ? 'Active (구독중)' : 'Disabled (중단됨)';
                const statusColor = row.is_active !== false ? 'background:#238636;color:#fff;' : 'background:#666;color:#fff;';
                
                return `<tr>
                    <td class="col-no">${no}</td>
                    <td style="font-weight:600">${row.email}</td>
                    <td>
                        <button class="status-btn" 
                                data-id="${row.id}" 
                                data-active="${row.is_active !== false}"
                                style="border:none; border-radius:4px; padding:4px 10px; cursor:pointer; font-size:12px; font-weight:600; ${statusColor}">
                            ${statusLabel}
                        </button>
                    </td>
                    <td style="color:var(--text-muted)">${dateText}</td>
                </tr>`;
            }).join('');

            // 클릭 이벤트로 상태 전환
            tbody.querySelectorAll('.status-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id = btn.getAttribute('data-id');
                    const currentActive = btn.getAttribute('data-active') === 'true';
                    const nextActive = !currentActive;

                    const { error: updateError } = await supabaseClient
                        .from('subscribers')
                        .update({ is_active: nextActive })
                        .eq('id', id);

                    if (updateError) {
                        alert('상태 변경 실패: ' + updateError.message);
                    } else {
                        // 성공하면 화면 새로고침 없이 바로 시각적 피드백
                        loadPage(currentPage);
                    }
                });
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:30px;">현재 구독자가 없습니다.</td></tr>';
        }

        renderPagination('pagination-container', currentPage, totalCount, PAGE_SIZE, loadPage);
    }

    await loadPage(0);
}
