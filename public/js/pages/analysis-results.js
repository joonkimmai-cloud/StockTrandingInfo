import { renderPagination } from './pagination.js';

const PAGE_SIZE = 15;

function escapeHTML(str) {
    if (typeof str !== 'string') return str || '';
    return str.replace(/[&<>"']/g, (m) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[m]));
}

function sanitizeQuery(str) {
    if (!str) return '';
    return str.replace(/[(),.]/g, ''); 
}

// market_summary / prediction 필드에 포함된 에러 JSON을 제거하고
// 사람이 읽기 좋은 메시지만 반환하는 정제 함수
function cleanSummary(text) {
    if (!text) return '내용 없음';

    // 1. "사유:" 키워드부터 그 뒤의 모든 내용(줄바꿈 포함)을 "기사를 참고해주세요."로 바꿉니다.
    // [\s\S]* 는 줄바꿈을 포함한 모든 문자를 의미합니다.
    let cleaned = text.replace(/사유:[\s\S]*$/g, '기사를 참고해주세요.');

    // 2. 혹시라도 남아있을 수 있는 JSON 찌꺼기들 (괄호, 콤마 등)을 한 번 더 제거합니다.
    cleaned = cleaned.replace(/\{[\s\S]*?\}/g, ''); // 중괄호 블록 제거
    cleaned = cleaned.replace(/[\[\]\{\}]/g, '');    // 개별 괄호 제거
    cleaned = cleaned.replace(/^\s*,\s*$/gm, '');   // 쉼표만 있는 줄 제거

    return cleaned.trim() || '내용 없음';
}


function translateSentiment(raw) {
    const s = (raw || '').toUpperCase();
    if (s.includes('BULL') || s.includes('BUY'))  return { label: '🔥 상승 우위', color: 'color:#155724; font-weight:700; background:#d4edda; padding:3px 8px; border-radius:4px;' };
    if (s.includes('BEAR') || s.includes('SELL')) return { label: '❄️ 하락 우위', color: 'color:#721c24; font-weight:700; background:#f8d7da; padding:3px 8px; border-radius:4px;' };
    return { label: '⚖️ 중립', color: 'color:#555; background:#eee; padding:3px 8px; border-radius:4px;' };
}

export async function renderAnalysisResults(container, supabase) {
    container.innerHTML = `
        <div class="page-header" style="display:flex; justify-content:space-between; align-items:flex-end;">
            <div>
                <h1 class="page-title">Analysis Results</h1>
                <p class="page-desc" id="analysis-count-text">AI가 분석한 종목별 투자 의견입니다.</p>
            </div>
            <div class="page-header-actions">
                <div class="search-container">
                    <input type="text" id="analysis-search-input" class="search-input" placeholder="분석 내용, 기업명, 의견 검색...">
                    <button id="analysis-search-btn" class="search-btn">🔍</button>
                </div>
            </div>
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
                    <span style="font-size:12px; color:#888; font-weight:400;">${escapeHTML(new Date(r.created_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' }))}</span>
                </div>
                <p style="white-space:pre-wrap; font-size:14px; margin-bottom:10px;"><b style="color:var(--primary-blue);">💡 시장 전체 요약:</b><br>${escapeHTML(cleanSummary(r.market_summary))}</p>
                <p style="white-space:pre-wrap; font-size:14px;"><b style="color:var(--primary-blue);">🎯 오늘의 예측 & 전략:</b><br>${escapeHTML(cleanSummary(r.prediction))}</p>
            </div>
        `;
    }

    let currentQuery = '';
    async function loadPage(page, query = currentQuery) {
        currentPage = page;
        currentQuery = query;
        const from = page * PAGE_SIZE;
        const to = from + PAGE_SIZE - 1;

        const tbody = document.getElementById('list-body');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px;">불러오는 중...</td></tr>';

        // !inner join is used to allow filtering by joined table fields
        let q = supabase.from('stock_analysis').select('*, companies!inner(name, symbol)', { count: 'exact' });
        
        if (query) {
            const safeQuery = sanitizeQuery(query);
            q = q.or(`sentiment.ilike.*${safeQuery}*,analysis_content.ilike.*${safeQuery}*,companies.name.ilike.*${safeQuery}*,companies.symbol.ilike.*${safeQuery}*`);
        }

        const { data, count, error } = await q
            .order('created_at', { ascending: false })
            .order('id', { ascending: false })
            .range(from, to);

        if (error) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:30px; color:red;">에러: ${error.message}</td></tr>`;
            return;
        }

        const totalCount = count || 0;
        document.getElementById('analysis-count-text').innerText = `AI가 분석한 종목별 투자 의견입니다. (총 ${totalCount}개${query ? ' 검색됨' : ''})`;

        if (data && data.length > 0) {
            tbody.innerHTML = data.map((item, i) => {
                const no = from + i + 1;
                const { label, color } = translateSentiment(item.sentiment);
                const compName = item.companies?.name || '알수없음';
                const compSymbol = item.companies?.symbol || '-';
                const dateText = new Date(item.created_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
                
                let analysisHtml = escapeHTML(item.analysis_content || '분석 내용 없음');
                // 만약 에러 폴백(기사 헤드라인)인 경우 그대로 보여주고,
                // 정상적인 분석 정보인 경우에는 헤더를 추가합니다.
                if (analysisHtml.includes('[기사 헤드라인]')) {
                    // 그대로 진행
                } else if (analysisHtml !== '분석 내용 없음') {
                    analysisHtml = `<b style="color:var(--success-color); display:block; margin-bottom:5px;">[AI 분석 정보]</b>${analysisHtml}`;
                }

                return `<tr>
                    <td class="col-no">${no}</td>
                    <td style="text-align:center;"><b>${escapeHTML(compName)}</b><br><span style="font-size:12px;color:#777;">(${escapeHTML(compSymbol)})</span></td>
                    <td style="text-align:center;"><span style="${escapeHTML(color)}">${escapeHTML(label)}</span></td>
                    <td style="white-space:pre-wrap; font-size:13px; line-height:1.5;">${analysisHtml}</td>
                    <td style="font-size:12px; color:#555; text-align:center;">${escapeHTML(dateText)}</td>
                </tr>`;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px;">아직 생성된 AI 분석 데이터가 없습니다.</td></tr>';
        }

        renderPagination('pagination-container', currentPage, totalCount, PAGE_SIZE, (p) => loadPage(p, currentQuery));
    }

    // 검색 이벤트 바인딩
    const searchInput = document.getElementById('analysis-search-input');
    const searchBtn = document.getElementById('analysis-search-btn');

    const handleSearch = () => {
        loadPage(0, searchInput.value.trim());
    };

    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });

    await loadPage(0);
}
