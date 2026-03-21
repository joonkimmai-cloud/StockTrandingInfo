export async function renderAnalysisResults(container, supabase) {
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
        // Fetch latest market report
        const { data: reports, error: reportErr } = await supabase
            .from('market_reports')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(1);

        // Fetch stock analysis
        const { data: analyses, error: analysisErr } = await supabase
            .from('stock_analysis')
            .select(`
                *,
                companies (name, symbol)
            `)
            .order('created_at', { ascending: false })
            .limit(50); // 최근 50개 제한

        if (reportErr && reportErr.details && !reportErr.message.includes("relation")) {
            console.error("Report fetch error", reportErr);
        }

        let html = '';

        if (reports && reports.length > 0) {
            const report = reports[0];
            html += `
                <div class="log-card" style="margin-bottom: 20px; background: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 8px;">
                    <h3 style="margin-top:0; border-bottom:1px solid #eee; padding-bottom:10px;">최근 시장 요약 리포트 <span style="font-size:12px; color:#888;">(${new Date(report.created_at).toLocaleString()})</span></h3>
                    <p style="white-space: pre-wrap; font-size: 14px; margin-bottom:10px;"><b style="color:var(--primary-blue);">💡 시장 전체 요약:</b><br/>${report.market_summary || '내용 없음'}</p>
                    <p style="white-space: pre-wrap; font-size: 14px; margin-bottom:10px;"><b style="color:var(--primary-blue);">🎯 오늘의 증시 예측:</b><br/>${report.prediction || '내용 없음'}</p>
                    <p style="white-space: pre-wrap; font-size: 14px;"><b style="color:var(--primary-blue);">🛡️ 투자(대응) 전략:</b><br/>${report.investment_strategy || '선택사항 없음'}</p>
                </div>
            `;
        }

        if (analyses && analyses.length > 0) {
            html += `
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
                <tbody>
            `;
            
            for (const item of analyses) {
                const sentimentText = (item.sentiment || 'N/A').toUpperCase();
                let sentimentColor = '';
                if (sentimentText.includes('BULL') || sentimentText.includes('BUY')) {
                    sentimentColor = 'color: #238636; font-weight: 700; background: #e6f6e6; padding: 3px 6px; border-radius: 4px;';
                } else if (sentimentText.includes('BEAR') || sentimentText.includes('SELL')) {
                    sentimentColor = 'color: #da3633; font-weight: 700; background: #ffe6e6; padding: 3px 6px; border-radius: 4px;';
                } else {
                    sentimentColor = 'color: #555; background: #eee; padding: 3px 6px; border-radius: 4px;';
                }
                                       
                const compName = item.companies ? item.companies.name : '알수없음(미등록)';
                const compSymbol = item.companies ? item.companies.symbol : '-';

                html += `
                    <tr>
                        <td style="text-align:center;"><b>${compName}</b><br/><span style="font-size:12px;color:#777;">(${compSymbol})</span></td>
                        <td style="text-align:center;"><span style="${sentimentColor}">${sentimentText}</span></td>
                        <td style="white-space: pre-wrap; font-size: 13px; line-height: 1.5;">${item.analysis_content || '분석 내용 없음'}</td>
                        <td style="font-size: 12px; color: #555; text-align:center;">${new Date(item.created_at).toLocaleString()}</td>
                    </tr>
                `;
            }
            html += `</tbody></table></div>`;
        } else {
            html += `<div class="empty-state">아직 생성된 AI 분석 데이터가 없습니다.<br>오늘의 배치가 돌고 나면 여기에 표시됩니다.</div>`;
        }

        document.getElementById('analysis-content').innerHTML = html;

    } catch (e) {
        document.getElementById('analysis-content').innerHTML = `<div class="empty-state" style="color:var(--error-color)">데이터를 불러오는 중 오류가 발생했습니다.<br>상세: ${e.message}</div>`;
        console.error("Analysis Load Error:", e);
    }
}
