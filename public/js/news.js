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
const pageSize = 50;

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

/**
 * 뉴스(AI 분석) 목록을 화면에 렌더링하는 핵심 함수
 * @param {number} page - 불러올 페이지 번호 (기본값 1)
 */
async function renderList(page = 1) {
    // 1. 현재 출력 중인 페이지 번호를 전역 변수에 저장
    currentPg = page;
    
    // 2. 화면 전환
    document.getElementById('news-list-view').style.display = 'block';
    document.getElementById('news-detail-view').style.display = 'none';
    
    const body = document.getElementById('news-list-body');
    const pagination = document.getElementById('pagination-controls');
    
    body.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:50px;">뉴스 데이터를 불러오는 중입니다...</td></tr>';
    pagination.innerHTML = '';

    try {
        const offset = (page - 1) * pageSize;
        
        // stock_analysis 대신 news_articles를 기본으로 가져옵니다.
        const query = `select=*,companies(name,market)&order=published_at.desc&limit=${pageSize}&offset=${offset}`;
        const headers = { 'Prefer': 'count=exact' };

        const { data: newsData, total } = await sbGet('news_articles', query, headers);

        if (!newsData || newsData.length === 0) {
            body.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:50px;">표시할 뉴스가 없습니다.</td></tr>';
            return;
        }

        body.innerHTML = '';
        
        // 해당 회사들의 분석 정보를 미리 가져와서 매핑합니다 (Batch fetch)
        const companyIds = [...new Set(newsData.map(n => n.company_id))];
        const anaData = await sbGet('stock_analysis', `company_id=in.(${companyIds.join(',')})&order=created_at.desc`);
        const anaMap = new Map();
        if (anaData && anaData.length > 0) {
            anaData.forEach(a => {
                if (!anaMap.has(a.company_id)) anaMap.set(a.company_id, a);
            });
        }

        // 중복 제거 및 리스트 구성 (날짜별 + 기업별)
        const uniqueEntries = [];
        const seenKeys = new Set();
        
        newsData.forEach(item => {
            const compName = item.companies?.name || 'Unknown';
            const dateStr = new Date(item.published_at).toISOString().split('T')[0];
            const key = `${compName}_${dateStr}`;

            if (!seenKeys.has(key)) {
                // 이 항목에 대한 분석 정보가 있는지 확인
                const analysis = anaMap.get(item.company_id);
                uniqueEntries.push({ ...item, analysis });
                seenKeys.add(key);
            }
        });

        uniqueEntries.forEach(item => {
            const date = new Date(item.published_at).toLocaleString('ko-KR', {
                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });

            // AI 분석 정보가 있으면 분석 내용을 우선 보여주고, 없으면 뉴스 타이틀을 보여줍니다.
            let insightPreview = '';
            let targetId = '';

            if (item.analysis && item.analysis.analysis_content && item.analysis.analysis_content.trim() !== '') {
                insightPreview = item.analysis.analysis_content;
                targetId = item.analysis.id;
            } else {
                insightPreview = item.title || '뉴스 제목 없음';
                targetId = 'art_' + item.id;
            }
            
            insightPreview = insightPreview.replace(/\[AI 텍스트 분석 지연[^\]]*\]/g, '').trim();
            insightPreview = insightPreview.replace(/[#*`>]/g, '').replace(/\n+/g, ' ').trim();
            
            if (insightPreview.length > 80) {
                insightPreview = insightPreview.substring(0, 80) + '...';
            }

            const row = `
                <tr onclick="location.href='news.html?id=${escapeHTML(targetId)}'">
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
    if (totalPages === 0) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';
    html += `<button class="pg-btn" ${currentPg === 1 ? 'disabled' : ''} onclick="renderList(${currentPg - 1})">이전</button>`;

    let startPage = Math.max(1, currentPg - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);
    endPage = Math.min(totalPages, endPage);

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
        let ana = null;
        let companyId = null;
        let isOnlyNews = false;

        if (id.startsWith('art_')) {
            // 뉴스 기사 기반 상세 (분석 없음)
            const artId = id.replace('art_', '');
            const artResults = await sbGet('news_articles', `id=eq.${artId}&select=*,companies(*)`);
            if (!artResults || artResults.length === 0) {
                alert('기사 정보를 찾을 수 없습니다.');
                goToList();
                return;
            }
            const art = artResults[0];
            companyId = art.company_id;
            isOnlyNews = true;
            ana = {
                companies: art.companies,
                created_at: art.published_at,
                analysis_content: null, // 타이틀만 보여주기 위함
                news_title: art.title
            };
        } else {
            // AI 분석 기반 상세
            const results = await sbGet('stock_analysis', `id=eq.${id}&select=*,companies(*)`);
            if (!results || results.length === 0) {
                alert('분석 정보를 찾을 수 없습니다.');
                goToList();
                return;
            }
            ana = results[0];
            companyId = ana.company_id;
        }

        document.getElementById('detail-company').innerText = ana.companies?.name || 'N/A';
        document.getElementById('detail-title').innerText = `${ana.companies?.name || '종목'} ${isOnlyNews ? '최신 소식' : 'AI 투자 인사이트 리포트'}`;
        
        document.getElementById('detail-date').innerText = new Date(ana.created_at).toLocaleString('ko-KR', {
            year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });

        const aiBox = document.getElementById('ai-content');
        const sentimentTag = document.getElementById('ai-sentiment');
        
        if (ana.analysis_content && ana.analysis_content.trim() !== '') {
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
            // AI 분석 정보가 없으면 뉴스 타이틀을 크게 보여줌
            // 만약 ana.news_title이 없으면 (stock_analysis에서 왔는데 분석내용만 없는 경우) 기사에서 가져와야 함
            let displayTitle = ana.news_title;
            if (!displayTitle) {
                const latestArt = await sbGet('news_articles', `company_id=eq.${companyId}&order=published_at.desc&limit=1&select=title`);
                displayTitle = (latestArt && latestArt.length > 0) ? latestArt[0].title : '수집된 분석 정보가 없습니다.';
            }
            aiBox.innerHTML = `<div style="padding: 20px; background: #f8fafc; border-radius: 12px; border-left: 5px solid #004e92; margin-top:10px;">
                <h3 style="margin:0; font-size:1.4rem; color:#1e293b; line-height:1.4;">${escapeHTML(displayTitle)}</h3>
                <p style="color:#64748b; margin-top:10px; font-size:0.95rem;">※ 해당 종목의 AI 분석 리포트가 아직 준비되지 않았습니다. 최신 기사 타이틀을 우선 안내해 드립니다.</p>
            </div>`;
            sentimentTag.style.display = 'none';
        }

        // 관련 기사 목록 조회
        const dateStr = ana.created_at.split('T')[0];
        const newsResults = await sbGet('news_articles', `company_id=eq.${companyId}&published_at=gte.${dateStr}&order=published_at.desc&limit=10`);
        
        const articlesList = document.getElementById('source-articles-list');
        if (newsResults && newsResults.length > 0) {
            let newsHtml = '<div class="news-detail-container">';
            newsResults.forEach(n => {
                const thumb = n.thumbnail_url ? `<img src="${n.thumbnail_url}" class="news-thumb" alt="thumbnail">` : '';
                newsHtml += `
                    <div class="news-item-card" onclick="window.open('${escapeHTML(n.source_url)}', '_blank')">
                        ${thumb}
                        <div class="news-text-content">
                            <h4 class="news-item-title">${escapeHTML(n.title)}</h4>
                            <p class="news-item-snippet">${escapeHTML(n.snippet || '')}</p>
                            <p class="news-item-summary">${escapeHTML(n.content || '').replace(/\n/g, '<br>')}</p>
                            <div class="news-item-footer">
                                <span class="news-source">${escapeHTML(n.source_name || '알 수 없음')}</span>
                                <span class="news-link-icon">원문 보기 ↗</span>
                            </div>
                        </div>
                    </div>
                `;
            });
            newsHtml += '</div>';
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
