const SUPABASE_URL = "https://fwptckxvhyzydrfralhw.supabase.co";
const SUPABASE_KEY = "sb_publishable_ZRdywELTvsTlfdU4SUCYsg_IASTgk3X";

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

function getParam(name) {
    return new URLSearchParams(window.location.search).get(name);
}

let currentPg = 1;
const pageSize = 15;

async function sbGet(table, query, headers = {}) {
    const url = `${SUPABASE_URL}/rest/v1/${table}?${query}`;
    const baseHeaders = { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` };
    const r = await fetch(url, {
        headers: { ...baseHeaders, ...headers }
    });
    
    if (headers['Prefer'] && headers['Prefer'].includes('count')) {
        const range = r.headers.get('content-range');
        const total = range ? parseInt(range.split('/')[1]) : 0;
        const data = await r.json();
        return { data, total };
    }
    
    return r.json();
}

async function loadPage() {
    const id = getParam('id');
    if (id) {
        renderDetail(id);
    } else {
        renderList(1);
    }
}

async function renderList(page = 1) {
    currentPg = page;
    document.getElementById('news-list-view').style.display = 'block';
    document.getElementById('news-detail-view').style.display = 'none';
    const body = document.getElementById('news-list-body');
    const pagination = document.getElementById('pagination-controls');
    
    body.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:50px;">데이터를 불러오는 중입니다...</td></tr>';
    pagination.innerHTML = '';

    try {
        const offset = (page - 1) * pageSize;
        const query = "select=*,companies(*)&order=published_at.desc";
        const headers = {
            'Prefer': 'count=exact',
            'Range': `${offset}-${offset + pageSize - 1}`
        };

        const { data, total } = await sbGet('news_articles', query, headers);

        if (!data || data.length === 0) {
            body.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:50px;">표시할 기사가 없습니다.</td></tr>';
            return;
        }

        body.innerHTML = '';
        data.forEach(article => {
            const date = new Date(article.published_at).toLocaleString('ko-KR', {
                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });

            const row = `
                <tr onclick="location.href='news.html?id=${escapeHTML(article.id)}'">
                    <td class="td-company">${escapeHTML(article.company_name || 'Stock Alpha')}</td>
                    <td class="td-title">${escapeHTML(article.title)}</td>
                    <td class="td-source">${escapeHTML(article.source_name || 'News Source')}</td>
                    <td class="td-date">${escapeHTML(date)}</td>
                </tr>
            `;
            body.insertAdjacentHTML('beforeend', row);
        });

        // 페이지네이션 렌더링
        renderPagination(total);
        window.scrollTo(0, 0);

    } catch (err) {
        console.error('renderList error:', err);
        body.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:50px; color:red;">데이터 로드 오류가 발생했습니다.</td></tr>';
    }
}

function renderPagination(totalCount) {
    const pagination = document.getElementById('pagination-controls');
    const totalPages = Math.ceil(totalCount / pageSize);
    if (totalPages <= 1) return;

    let html = '';
    
    // 이전 버튼
    html += `<button class="pg-btn" ${currentPg === 1 ? 'disabled' : ''} onclick="renderList(${currentPg - 1})">이전</button>`;

    // 페이지 번호 (최대 5개씩 표시)
    let startPage = Math.max(1, currentPg - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="pg-btn ${i === currentPg ? 'active' : ''}" onclick="renderList(${i})">${i}</button>`;
    }

    // 다음 버튼
    html += `<button class="pg-btn" ${currentPg === totalPages ? 'disabled' : ''} onclick="renderList(${currentPg + 1})">다음</button>`;

    pagination.innerHTML = html;
}

async function renderDetail(id) {
    document.getElementById('news-list-view').style.display = 'none';
    document.getElementById('news-detail-view').style.display = 'block';

    try {
        const results = await sbGet('news_articles', `id=eq.${id}&select=*,companies(*)`);
        if (!results || results.length === 0) {
            alert('기사를 찾을 수 없습니다.');
            goToList();
            return;
        }

        const a = results[0];
        document.getElementById('detail-company').innerText = a.company_name || 'N/A';
        document.getElementById('detail-title').innerText = a.title;
        document.getElementById('detail-date').innerText = new Date(a.published_at).toLocaleString('ko-KR', {
            year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
        document.getElementById('detail-source').innerText = a.source_name || 'News Source';
        
        // 원문 링크 설정
        const originalBtn = document.getElementById('detail-original-link');
        const sourceNameBtn = document.getElementById('detail-source-name-btn');
        if (a.source_url) {
            originalBtn.href = a.source_url;
            originalBtn.style.display = 'inline-flex';
            sourceNameBtn.innerText = a.source_name || '원문';
        } else {
            originalBtn.style.display = 'none';
        }
        
        // Markdown 렌더링 적용 (본문 내용 우선, 없으면 요약 표시)
        const rawContent = a.content || a.snippet || '본문 내용이 없습니다.';
        if (typeof marked !== 'undefined') {
            // Marked GFM 및 테이블 활성화
            document.getElementById('detail-content').innerHTML = marked.parse(rawContent, {
                gfm: true,
                breaks: true
            });
        } else {
            document.getElementById('detail-content').innerText = rawContent;
        }

        // AI 데이터 조회 (stock_analysis 테이블)
        const analysisResults = await sbGet('stock_analysis', `company_id=eq.${a.company_id}&order=created_at.desc&limit=1`);
        const aiBox = document.getElementById('ai-content');
        const sentimentTag = document.getElementById('ai-sentiment');

        if (analysisResults && analysisResults.length > 0) {
            const ana = analysisResults[0];
            const analysisHtml = typeof marked !== 'undefined' ? marked.parse(ana.analysis_content) : ana.analysis_content;
            aiBox.innerHTML = analysisHtml;
            
            // 감성 텍스트 한글 변환
            const sentimentMap = {
                'bullish': '📈 상승 우세',
                'bearish': '📉 하락 주의',
                'neutral': '⚖️ 중립'
            };
            const sent = (ana.sentiment || 'neutral').toLowerCase();
            sentimentTag.innerText = sentimentMap[sent] || '중립';
            sentimentTag.style.display = 'inline-block';
            
            // 감성 색상 지정
            sentimentTag.className = `sentiment-tag ${sent}`;
        } else {
            aiBox.innerHTML = "이 종목에 대한 최신 분석 데이터가 없습니다.<br><br>일일 종목 분석 보고서 생성을 기다려주세요.";
            sentimentTag.style.display = 'none';
        }

        // 스크롤 최상단으로
        window.scrollTo(0, 0);

    } catch (err) {
        console.error('renderDetail error:', err);
        alert('상세 정보를 불러오는 중 오류가 발생했습니다.');
        goToList();
    }
}

function goToList() {
    window.location.href = 'news.html';
}

window.onload = loadPage;
