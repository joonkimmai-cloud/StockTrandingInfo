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
    // 1. 현재 출력 중인 페이지 번호를 전역 변수에 저장 (페이지네이션 연동용)
    currentPg = page;
    
    // 2. 화면 전환: 목록 뷰는 보이고, 상세 뷰는 숨김 처리
    document.getElementById('news-list-view').style.display = 'block';
    document.getElementById('news-detail-view').style.display = 'none';
    
    // 3. 데이터를 채울 테이블 바디와 페이지네이션 컨트롤 요소 참조
    const body = document.getElementById('news-list-body');
    const pagination = document.getElementById('pagination-controls');
    
    // 5. 로딩 중임을 사용자에게 알리고 이전 페이지네이션 버튼 제거
    body.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:50px;">분석 데이터를 불러오는 중입니다...</td></tr>';
    pagination.innerHTML = '';

    try {
        // 6. DB 조회를 위한 오프셋 계산 (현재 페이지 기준)
        const offset = (page - 1) * pageSize;
        
        // 7. Supabase 쿼리 작성: stock_analysis 테이블에서 최신순으로 상위 200개 조회
        // (충분한 과거 데이터를 확보한 뒤 클라이언트에서 중복을 제거하기 위해 넉넉히 가져옴)
        const query = "select=*,companies(name,market)&order=created_at.desc&limit=200";
        const headers = {
            'Prefer': 'count=exact' // 전체 데이터 개수를 헤더로 받아오기 위함
        };

        // 8. API 호출 및 데이터 획득
        const { data, total } = await sbGet('stock_analysis', query, headers);

        // 9. 데이터가 없을 경우 처리
        if (!data || data.length === 0) {
            body.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:50px;">표시할 분석 결과가 없습니다.</td></tr>';
            return;
        }

        // 10. 기존 로딩 메시지 비우기
        body.innerHTML = '';
        
        // 11. 중복 제거 실시간 필터링: '날짜별 + 기업별'로 유니크하게 필터링
        // (하루에 한 종목당 하나의 분석 리포트만 목록에 보이도록 함)
        const uniqueEntries = [];
        const seenKeys = new Set(); // 이미 처리된 '기업_날짜' 키를 저장할 집합
        
        data.forEach(item => {
            const compName = item.companies?.name || 'Unknown';
            // 12. 생성된 날짜 정보에서 시간 제외한 '날짜(YYYY-MM-DD)' 부분만 추출
            const dateStr = new Date(item.created_at).toISOString().split('T')[0];
            const key = `${compName}_${dateStr}`; // 예: "삼성전자_2024-03-24"

            // 13. 동일 날짜에 처음 등장한 기업의 리포트만 리스트에 추가
            if (!seenKeys.has(key)) {
                uniqueEntries.push(item);
                seenKeys.add(key);
            }
        });

        // 14. 필터링 후에도 보여줄 기사가 없는 경우 처리
        if (uniqueEntries.length === 0) {
            body.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:50px;">표시할 분석 결과가 없습니다.</td></tr>';
            return;
        }

        // 15. 최종 필터링된 유니크 리스트를 순회하며 HTML 행(Row) 생성
        uniqueEntries.forEach(item => {
            // 16. 분석 날짜를 가독성 좋은 '월 일 시간' 형태로 변환
            const date = new Date(item.created_at).toLocaleString('ko-KR', {
                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });

            // 17. AI 분석 정보를 요약하여 목록용 텍스트로 가공
            let insightPreview = item.analysis_content || '분석 내용 없음';
            
            // 18. 시스템 관련 불필요한 접두어(예: [AI 텍스트 분석 지연...])가 있다면 제거
            insightPreview = insightPreview.replace(/\[AI 텍스트 분석 지연[^\]]*\]/g, '').trim();
            
            // 19. 마크다운 특수문자(#, *, ` 등) 및 불필요한 줄바꿈 제거
            insightPreview = insightPreview.replace(/[#*`>]/g, '').replace(/\n+/g, ' ').trim();
            
            // 20. 내용이 너무 길면 80자까지만 자르고 '...' 추가
            if (insightPreview.length > 80) {
                insightPreview = insightPreview.substring(0, 80) + '...';
            }

            // 21. 테이블 행 HTML 생성 및 클릭 시 상세 페이지(news.html?id=xxx) 이동 설정
            const row = `
                <tr onclick="location.href='news.html?id=${escapeHTML(item.id)}'">
                    <td class="td-company">${escapeHTML(item.companies?.name || 'short game')}</td>
                    <td class="td-title" style="color:#555; font-weight:400;">${escapeHTML(insightPreview)}</td>
                    <td class="td-date">${escapeHTML(date)}</td>
                </tr>
            `;
            // 22. 생성된 행을 테이블 바디 하단에 추가
            body.insertAdjacentHTML('beforeend', row);
        });

        // 23. 하단 페이지네이션 버튼 생성 (전체 개수 기준)
        renderPagination(total);
        
        // 24. 페이지 로딩 완료 후 화면 상단으로 스크롤 이동
        window.scrollTo(0, 0);

    } catch (err) {
        // 25. 에러 발생 시 로그를 남기고 사용자에게 오류 메시지 출력
        console.error('renderList error:', err);
        body.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:50px; color:red;">데이터 로드 오류가 발생했습니다.</td></tr>';
    }
}

function renderPagination(totalCount) {
    const pagination = document.getElementById('pagination-controls');
    const totalPages = Math.ceil(totalCount / pageSize);
    // 1페이지만 있어도 번호를 표시하도록 수정 (기존: totalPages <= 1 이면 return)
    if (totalPages === 0) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';
    // 이전 버튼 (1페이지면 비활성화)
    html += `<button class="pg-btn" ${currentPg === 1 ? 'disabled' : ''} onclick="renderList(${currentPg - 1})">이전</button>`;

    // 페이지 번호 범위 계산 (현재 페이지 기준 좌우 2개씩, 최대 5개)
    let startPage = Math.max(1, currentPg - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);
    
    // 최종 보정: endPage가 totalPages를 넘지 않도록
    endPage = Math.min(totalPages, endPage);

    // 페이지 버튼 생성
    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="pg-btn ${i === currentPg ? 'active' : ''}" onclick="renderList(${i})">${i}</button>`;
    }

    // 다음 버튼 (마지막 페이지면 비활성화)
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
