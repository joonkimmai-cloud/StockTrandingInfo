import { renderPagination } from './pagination.js';

const PAGE_SIZE = 15;

function translateSentiment(raw) {
    const s = (raw || '').toUpperCase();
    if (s.includes('BULL') || s.includes('BUY'))  return { label: '🔥 상승 우위', color: 'color:#155724; font-weight:700; background:#d4edda; padding:3px 8px; border-radius:4px;' };
    if (s.includes('BEAR') || s.includes('SELL')) return { label: '❄️ 하락 우위', color: 'color:#721c24; font-weight:700; background:#f8d7da; padding:3px 8px; border-radius:4px;' };
    return { label: '⚖️ 중립', color: 'color:#555; background:#eee; padding:3px 8px; border-radius:4px;' };
}

export async function renderAnalysisResults(container, supabase) {
    let currentPage = 0;

    // AI 분석 건수
    const { count } = await supabase
        .from('stock_analysis')
        .select('*', { count: 'exact', head: true });

    const totalCount = count || 0;

    container.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Analysis Results (AI 분석 결과)</h1>
            <p class="page-desc">AI가 분석한 종목별 투자 의견 및 시장 요약입니다. (총 ${totalCount}개)</p>
        </div>
        <div id="market-report-section"></div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th class="col-no">#</th>
                        <th style="width:15%">종목명 (심볼)</th>
                        <th style="width:12%">투자의견</th>
                        <th>AI 핵심 분석 내용</th>
                        <th style="width:13%">분석 일자</th>
                    </tr>
                </thead>
                <tbody id="list-body"></tbody>
            </table>
            <div id="pagination-container"></div>
        </div>
    `;

    // 최신 마켓 리포트 1건 표시
    const { data: reports } = await supabase
        .from('market_reports')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(1);

    const reportSection = document.getElementById('market-report-section');
    if (reports && reports.length > 0) {
        const r = reports[0];
        reportSection.innerHTML = `
            <div class="card" style="margin-bottom:16px;">
                <div class="card-title">최근 시장 요약 리포트
                    <span style="font-size:12px; color:#888; font-weight:400;">${new Date(r.created_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })}</span>
                </div>
                <p style="white-space:pre-wrap; font-size:14px; margin-bottom:10px;"><b style="color:var(--primary-blue);">💡 시장 전체 요약:</b><br>${r.market_summary || '내용 없음'}</p>
                <p style="white-space:pre-wrap; font-size:14px;"><b style="color:var(--primary-blue);">🎯 오늘의 예측 & 전략:</b><br>${r.prediction || '내용 없음'}</p>
            </div>
        `;
    }

    async function loadPage(page) {
        currentPage = page;
        const from = page * PAGE_SIZE;
        const to = from + PAGE_SIZE - 1;

        const { data } = await supabase
            .from('stock_analysis')
            .select('*, companies (name, symbol)')
            .order('created_at', { ascending: false })
            .range(from, to);

        const tbody = document.getElementById('list-body');
        if (!tbody) return;

        if (data && data.length > 0) {
            tbody.innerHTML = data.map((item, i) => {
                const no = from + i + 1;
                const { label, color } = translateSentiment(item.sentiment);
                const compName = item.companies?.name || '알수없음';
                const compSymbol = item.companies?.symbol || '-';
                const dateText = new Date(item.created_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
                return `<tr>
                    <td class="col-no">${no}</td>
                    <td style="text-align:center;"><b>${compName}</b><br><span style="font-size:12px;color:#777;">(${compSymbol})</span></td>
                    <td style="text-align:center;"><span style="${color}">${label}</span></td>
                    <td style="white-space:pre-wrap; font-size:13px; line-height:1.5;">${item.analysis_content || '분석 내용 없음'}</td>
                    <td style="font-size:12px; color:#555; text-align:center;">${dateText}</td>
                </tr>`;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px;">아직 생성된 AI 분석 데이터가 없습니다.</td></tr>';
        }

        renderPagination('pagination-container', currentPage, totalCount, PAGE_SIZE, loadPage);
    }

    await loadPage(0);
}
