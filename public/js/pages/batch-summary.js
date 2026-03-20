// ==========================================
// 배치(자동 작업) 요약 페이지를 화면에 그리는 함수
// ==========================================
export async function renderBatchSummary(contentEl, supabaseClient) {
    // 1. 데이터베이스(Supabase)에서 가장 최근의 기록 10개를 가져옵니다. (시간 역순 정렬)
    const { data } = await supabaseClient
        .from('batch_summary')
        .select('*')
        .order('last_run_at', { ascending: false })
        .limit(10);

    // 2. 화면(HTML)에 그려질 뼈대를 만듭니다. (초보자를 위한 UI 템플릿)
    contentEl.innerHTML = `
        <div class="page-header">
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <div>
                    <h1 class="page-title">Batch Summary</h1>
                    <p class="page-desc">최근 10건의 배치(자동 작업) 실행 기록 및 성공/실패 여부를 모니터링합니다.</p>
                </div>
                <!-- 배치를 지금 바로 실행시키는 초록색 버튼 -->
                <button id="run-batch-btn" class="btn-run-batch">
                    <span id="run-btn-text">Run Batch Now</span>
                </button>
            </div>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th>실행 시간 (Run Time)</th>
                        <th>상태 (Status)</th>
                        <th>요약 정보 (Summary)</th>
                        <th>성공/실패 (Success/Fail)</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- 데이터를 반복문을 통해 표의 각 행(row)으로 만들어줍니다. -->
                    ${data?.map(row => {
                        // 로그 안의 특수문자나 띄어쓰기를 안전하게 전달하기 위해서 문자를 암호화(Base64)합니다.
                        const logBase64 = btoa(unescape(encodeURIComponent(row.log_content || 'No log content available.')));
                        
                        // 완성된 각 행의 HTML(테이블 줄) 구조 리턴
                        return `
                        <!-- 이 줄을 마우스로 누르면 showPastLog 함수가 동작하여 팝업(모달)창이 열립니다! -->
                        <tr class="clickable-row" onclick="window.showPastLog('${logBase64}', '${row.last_status}')">
                            <td style="color:var(--text-muted)">${new Date(row.last_run_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })}</td>
                            <td>
                                <!-- 상태에 따라 점(dot) 색상을 바꿈 -->
                                <span class="status-dot ${row.last_status ? row.last_status.toLowerCase() : 'fail'}"></span>
                                <b>${row.last_status || 'UNKNOWN'}</b>
                            </td>
                            <td>${row.summary_message || '-'}</td>
                            <td>${row.success_count || 0} / ${row.fail_count || 0}</td>
                        </tr>
                        `;
                    }).join('') || '<tr><td colspan="4">No data available (데이터 없음)</td></tr>'}
                </tbody>
            </table>
        </div>
    `;

    // 3. 만들어진 'Run Batch Now' 버튼에 클릭 이벤트 추가
    const btn = document.getElementById('run-batch-btn');
    if (btn) btn.addEventListener('click', window.handleRunBatch);

    // 4. API 서버가 현재 배치 중인지 확인하는 함수 호출
    if (typeof window.checkBatchStatus === 'function') {
        window.checkBatchStatus();
    }
}
