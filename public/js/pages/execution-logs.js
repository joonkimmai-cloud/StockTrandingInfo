let currentPage = 0;
const PAGE_SIZE = 15;
let isEndOfData = false;

export async function renderExecutionLogs(contentEl, supabaseClient) {
    currentPage = 0;
    isEndOfData = false;

    contentEl.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Execution Logs (실행 로그 관리)</h1>
            <p class="page-desc">자동 작업(Batch)이 진행되는 과정에서의 주요 단계별 기록(로그)을 확인할 수 있습니다.</p>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th style="width: 15%">발생 시간 (Time)</th>
                        <th style="width: 20%">진행 단계 (Step)</th>
                        <th style="width: 15%">상태 (Status)</th>
                        <th style="width: 50%">상세 메시지 (Message)</th>
                    </tr>
                </thead>
                <tbody id="log-list-body">
                </tbody>
            </table>
            <div style="text-align: center; margin-top: 15px; padding: 10px;">
                <button id="load-more-btn" class="btn-blue" style="width: 200px;">더 보기 (Load More)</button>
            </div>
        </div>
    `;

    document.getElementById('load-more-btn').addEventListener('click', async () => {
        await fetchAndRenderData(supabaseClient);
    });

    await fetchAndRenderData(supabaseClient);
}

async function fetchAndRenderData(supabaseClient) {
    if (isEndOfData) return;
    
    const btn = document.getElementById('load-more-btn');
    btn.innerText = "불러오는 중...";
    btn.disabled = true;

    try {
        const { data, error } = await supabaseClient
            .from('execution_logs')
            .select('*')
            .order('created_at', { ascending: false })
            .range(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE - 1);

        if (error) throw error;

        const tbody = document.getElementById('log-list-body');

        if (data && data.length > 0) {
            data.forEach(row => {
                const tr = document.createElement('tr');
                const dateText = new Date(row.created_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
                const statusClass = row.status.toLowerCase();
                tr.innerHTML = `
                    <td style="color:var(--text-muted); font-size: 0.8rem;">${dateText}</td>
                    <td style="font-weight:600">${row.step_name}</td>
                    <td>
                        <span class="status-dot ${statusClass}"></span>
                        ${row.status}
                    </td>
                    <td style="font-size:0.85rem">${row.log_message}</td>
                `;
                tbody.appendChild(tr);
            });

            currentPage++;

            if (data.length < PAGE_SIZE) {
                isEndOfData = true;
                btn.style.display = 'none';
            }
        } else {
            isEndOfData = true;
            btn.style.display = 'none';
            if (currentPage === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No logs available (로그가 없습니다.)</td></tr>';
            }
        }
    } catch (err) {
        console.error("데이터 로드 중 에러:", err);
        alert("데이터를 가져오는 중 오류가 발생했습니다.");
    } finally {
        btn.innerText = "더 보기 (Load More)";
        btn.disabled = false;
    }
}
