let currentPage = 0;
const PAGE_SIZE = 15;
let isEndOfData = false;
let globalSupabase = null;

export async function renderAnalysisResults(container, supabase) {
    globalSupabase = supabase;
    currentPage = 0;
    isEndOfData = false;

    container.innerHTML = `
        <div class="data-header">
            <h2>Analysis Results (AI 분석 결과)</h2>
            <button class="btn-blue" onclick="loadPage('analysis-results')">새로고침(Refresh)</button>
        </div>
        <div id="analysis-content">
            <div style="padding: 40px; text-align: center;"><div class="loader"></div> 데이터를 불러오는 중입니다...</div>
        </div>
    `;

    try {
        // Fetch latest market report once
        const { data: reports, error: reportErr } = await supabase
            .from('market_reports')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(1);

        let reportHtml = '';
        if (reports && reports.length > 0) {
            const report = reports[0];
            reportHtml = `
                <div class="log-card" style="margin-bottom: 20px; background: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 8px;">
                    <h3 style="margin-top:0; border-bottom:1px solid #eee; padding-bottom:10px;">최근 시장 요약 리포트 <span style="font-size:12px; color:#888;">(${new Date(report.created_at).toLocaleString()})</span></h3>
                    <p style="white-space: pre-wrap; font-size: 14px; margin-bottom:10px;"><b style="color:var(--primary-blue);">💡 시장 전체 요약:</b><br/>${report.market_summary || '내용 없음'}</p>
                    <p style="white-space: pre-wrap; font-size: 14px; margin-bottom:10px;"><b style="color:var(--primary-blue);">🎯 오늘의 증시 예측:</b><br/>${report.prediction || '내용 없음'}</p>
                    <p style="white-space: pre-wrap; font-size: 14px;"><b style="color:var(--primary-blue);">🛡️ 투자(대응) 전략:</b><br/>${report.investment_strategy || '선택사항 없음'}</p>
                </div>
            `;
        }

        // Draw Skeleton for Stock Analysis List
        document.getElementById('analysis-content').innerHTML = `
            ${reportHtml}
            <div style="background: #fff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th width="15%">종목명 (심볼)</th>
                            <th width="10%">투성의견<br/>(Sentiment)</th>
                            <th width="60%">AI 핵심 분석 내용</th>
                            <th width="15%">조회 일자</th>
                        </tr>
                    </thead>
                    <tbody id="analysis-list-body">
                    </tbody>
                </table>
                <div style="text-align: center; margin-top: 15px; padding: 10px;">
                    <button id="load-more-btn" class="btn-blue" style="width: 200px;">더 보기 (Load More)</button>
                </div>
            </div>
        `;

        document.getElementById('load-more-btn').addEventListener('click', fetchAndRenderData);
        
        await fetchAndRenderData();

    } catch (e) {
        document.getElementById('analysis-content').innerHTML = `<div class="empty-state" style="color:var(--error-color)">데이터를 초기화하는 중 오류가 발생했습니다.<br>상세: ${e.message}</div>`;
        console.error("Analysis Init Error:", e);
    }
}

function translateSentiment(raw) {
    const s = (raw || '').toUpperCase();
    if (s.includes('BULL') || s.includes('BUY'))  return { label: '🔥 상승 우위', color: 'color:#155724; font-weight:700; background:#d4edda; padding:3px 8px; border-radius:4px;' };
    if (s.includes('BEAR') || s.includes('SELL')) return { label: '❄️ 하락 우위', color: 'color:#721c24; font-weight:700; background:#f8d7da; padding:3px 8px; border-radius:4px;' };
    return { label: '⚖️ 중립', color: 'color:#555; background:#eee; padding:3px 8px; border-radius:4px;' };
}

async function fetchAndRenderData() {
    if (isEndOfData) return;
    
    const btn = document.getElementById('load-more-btn');
    if (!btn) return;
    btn.innerText = "불러오는 중...";
    btn.disabled = true;

    try {
        const { data: analyses, error: analysisErr } = await globalSupabase
            .from('stock_analysis')
            .select('*, companies (name, symbol)')
            .order('created_at', { ascending: false })
            .range(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE - 1);

        if (analysisErr) throw analysisErr;

        const tbody = document.getElementById('analysis-list-body');

        if (analyses && analyses.length > 0) {
            analyses.forEach(item => {
                const { label: sentimentLabel, color: sentimentColor } = translateSentiment(item.sentiment);
                               
                const compName = item.companies ? item.companies.name : '알수없음(미등록)';
                const compSymbol = item.companies ? item.companies.symbol : '-';

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="text-align:center;"><b>${compName}</b><br/><span style="font-size:12px;color:#777;">(${compSymbol})</span></td>
                    <td style="text-align:center;"><span style="${sentimentColor}">${sentimentLabel}</span></td>
                    <td style="white-space: pre-wrap; font-size: 13px; line-height: 1.5;">${item.analysis_content || '분석 내용 없음'}</td>
                    <td style="font-size: 12px; color: #555; text-align:center;">${new Date(item.created_at).toLocaleString()}</td>
                `;
                tbody.appendChild(tr);
            });


            currentPage++;

            if (analyses.length < PAGE_SIZE) {
                isEndOfData = true;
                btn.style.display = 'none';
            }
        } else {
            isEndOfData = true;
            btn.style.display = 'none';
            if (currentPage === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 30px;">아직 생성된 AI 분석 데이터가 없습니다.<br>오늘의 배치가 돌고 나면 여기에 표시됩니다.</td></tr>';
            }
        }
    } catch (err) {
        console.error("분석 데이터 로드 에러:", err);
        alert("목록을 가져오는 중 오류가 발생했습니다.");
    } finally {
        if (btn) {
            btn.innerText = "더 보기 (Load More)";
            btn.disabled = false;
        }
    }
}
