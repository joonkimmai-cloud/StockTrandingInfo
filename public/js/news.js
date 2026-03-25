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
    
    body.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:50px;">분석 데이터를 불러오는 중입니다...</td></tr>';
    pagination.innerHTML = '';

    try {
        const offset = (page - 1) * pageSize;
        // stock_analysis 테이블 중심 조회 (AI 분석이 있는 것만)
        const query = "select=*,companies(name,market)&analysis_content=not.is.null&order=created_at.desc";
        const headers = {
            'Prefer': 'count=exact',
            'Range': `${offset}-${offset + pageSize - 1}`
        };

        const { data, total } = await sbGet('stock_analysis', query, headers);

        if (!data || data.length === 0) {
            body.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:50px;">표시할 분석 결과가 없습니다.</td></tr>';
            return;
        }

        body.innerHTML = '';
        data.forEach(item => {
            const date = new Date(item.created_at).toLocaleString('ko-KR', {
                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });

            // AI 인사이트 요약 (첫 100자 정도만 표시)
            const insightPreview = item.analysis_content ? item.analysis_content.substring(0, 80).replace(/[#*`]/g, '') + '...' : '분석 내용 없음';

            const row = `
                <tr onclick="location.href='news.html?id=${escapeHTML(item.id)}'">
                    <td class="td-company">${escapeHTML(item.companies?.name || 'short game')}</td>
                    <td class="td-title" style="color:#555; font-weight:400;">${escapeHTML(insightPreview)}</td>
                    <td class="td-date">${escapeHTML(date)}</td>
                </tr>
            `;
            body.insertAdjacentHTML('beforeend', row);
        });

        renderPagination(total);
        window.scrollTo(0, 0);

    } catch (err) {
        console.error('renderList error:', err);
        body.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:50px; color:red;">데이터 로드 오류가 발생했습니다.</td></tr>';
    }
}

function renderPagination(totalCount) {
    const pagination = document.getElementById('pagination-controls');
    const totalPages = Math.ceil(totalCount / pageSize);
    if (totalPages <= 1) return;

    let html = '';
    html += `<button class="pg-btn" ${currentPg === 1 ? 'disabled' : ''} onclick="renderList(${currentPg - 1})">이전</button>`;

    let startPage = Math.max(1, currentPg - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="pg-btn ${i === currentPg ? 'active' : ''}" onclick="renderList(${i})">${i}</button>`;
    }

    html += `<button class="pg-btn" ${currentPg === totalPages ? 'disabled' : ''} onclick="renderList(${currentPg + 1})">다음</button>`;
    pagination.innerHTML = html;
}

async function renderDetail(id) {
    document.getElementById('news-list-view').style.display = 'none';
    document.getElementById('news-detail-view').style.display = 'block';

    try {
        // 1. AI 분석 정보 조회
        const results = await sbGet('stock_analysis', `id=eq.${id}&select=*,companies(*)`);
        if (!results || results.length === 0) {
            alert('분석 정보를 찾을 수 없습니다.');
            goToList();
            return;
        }

        const ana = results[0];
        document.getElementById('detail-company').innerText = ana.companies?.name || 'N/A';
        document.getElementById('detail-title').innerText = `${ana.companies?.name || '종목'} AI 투자 인사이트 리포트`;
        
        document.getElementById('detail-date').innerText = new Date(ana.created_at).toLocaleString('ko-KR', {
            year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });

        // AI 분석 내용 렌더링
        const aiBox = document.getElementById('ai-content');
        const sentimentTag = document.getElementById('ai-sentiment');
        
        if (ana.analysis_content) {
            aiBox.innerHTML = typeof marked !== 'undefined' ? marked.parse(ana.analysis_content) : ana.analysis_content;
            
            const sentimentMap = {
                'bullish': '📈 상승 우세',
                'bearish': '📉 하락 주의',
                'neutral': '⚖️ 중립'
            };
            const sent = (ana.sentiment || 'neutral').toLowerCase();
            sentimentTag.innerText = sentimentMap[sent] || '중립';
            sentimentTag.className = `sentiment-tag ${sent}`;
            sentimentTag.style.display = 'inline-block';
        } else {
            aiBox.innerHTML = "분석 내용이 비어있습니다.";
            sentimentTag.style.display = 'none';
        }

        // 2. 관련 기사 목록 조회 (동일 종목, 비슷한 시간대 수집된 기사)
        const dateStr = ana.created_at.split('T')[0];
        const newsResults = await sbGet('news_articles', `company_id=eq.${ana.company_id}&published_at=gte.${dateStr}&order=published_at.desc&limit=10`);
        
        const articlesList = document.getElementById('source-articles-list');
        if (newsResults && newsResults.length > 0) {
            let newsHtml = '<ul style="list-style:none; padding:0;">';
            newsResults.forEach(n => {
                newsHtml += `
                    <li style="margin-bottom: 12px; padding: 10px; border-bottom: 1px dotted #eee;">
                        <a href="${escapeHTML(n.source_url)}" target="_blank" style="text-decoration:none; color:var(--primary-color); font-weight:600; display:block; margin-bottom:4px;">
                            ${escapeHTML(n.title)} <span style="font-size:12px; font-weight:normal; color:#999;">↗</span>
                        </a>
                        <span style="font-size:12px; color:#888;">출처: ${escapeHTML(n.source_name || '알 수 없음')}</span>
                    </li>
                `;
            });
            newsHtml += '</ul>';
            articlesList.innerHTML = newsHtml;
        } else {
            articlesList.innerHTML = '<div style="color:#999; padding:20px;">수집된 관련 기사가 없습니다.</div>';
        }

        window.scrollTo(0, 0);

    } catch (err) {
        console.error('renderDetail error:', err);
        alert('상세를 불러오는 중 오류가 발생했습니다.');
        goToList();
    }
}

function goToList() {
    window.location.href = 'news.html';
}

window.onload = loadPage;
