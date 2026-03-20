// ==========================================
// 배치(자동 작업) 프로세스 도중 발생한 
// 단계별 '로그(기록)' 데이터를 표시하는 페이지
// ==========================================
export async function renderExecutionLogs(contentEl, supabaseClient) {
    // 1. Supabase(데이터베이스)에서 30개까지의 로그를 최근 순으로 가져옵니다.
    const { data } = await supabaseClient
        .from('execution_logs')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(30);

    // 2. 그려질 화면(HTML) 준비.
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
                <tbody>
                    <!-- 데이터가 있는 경우 map(반복)을 통해서, 없는 경우 없다는 안내를 뿌려줌 -->
                    ${data?.map(row => `
                        <tr>
                            <!-- 시간 정보 표기 (회색, 작은 폰트) -->
                            <td style="color:var(--text-muted); font-size: 0.8rem;">
                                ${new Date(row.created_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })}
                            </td>
                            <!-- 어떤 단계가 진행중인지 표기 -->
                            <td style="font-weight:600">${row.step_name}</td>
                            <!-- 성공/실패 여부를 색상 동그라미로 함께 표시 -->
                            <td>
                                <span class="status-dot ${row.status.toLowerCase()}"></span>
                                ${row.status}
                            </td>
                            <!-- 문제가 생겼을 때의 에러 내용이나, 정상 완료 메세지 -->
                            <td style="font-size:0.85rem">${row.log_message}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="4">No logs available (로그가 없습니다.)</td></tr>'}
                </tbody>
            </table>
        </div>
    `;
}
