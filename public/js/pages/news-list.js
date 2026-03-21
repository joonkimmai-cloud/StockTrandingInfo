import { renderPagination } from './pagination.js';

const PAGE_SIZE = 15;

export async function renderNewsList(container, supabase) {
    // 1. 초기 뼈대 그리기
    container.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title">Scraped News List</h1>
                <p class="page-desc" id="news-count-text">최근 수집된 뉴스 기사 목록입니다. 클릭하면 상세 내용을 확인하실 수 있습니다.</p>
            </div>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th style="width:50px;">#</th>
                        <th style="width:120px;">기업명</th>
                        <th>뉴스 타이틀</th>
                        <th style="width:100px;">언론사</th>
                        <th style="width:160px;">수집 일자</th>
                    </tr>
                </thead>
                <tbody id="list-body">
                    <!-- 데이터 로딩 중 -->
                </tbody>
            </table>
            <div id="pagination-container"></div>
        </div>
    `;

    let currentPage = 0;
    
    // 전체 개수 가져와서 상단에 표시
    const { count: totalCount } = await supabase
        .from('news_articles')
        .select('*', { count: 'exact', head: true });
    
    document.getElementById('news-count-text').innerText = `최근 수집된 뉴스 기사 목록입니다. (총 ${totalCount || 0}건)`;

    // 실제 데이터 한 페이지씩 불러오는 함수
    async function loadPage(page) {
        currentPage = page;
        const from = page * PAGE_SIZE;
        const to = from + PAGE_SIZE - 1;

        const tbody = document.getElementById('list-body');
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:20px;">불러오는 중...</td></tr>`;

        const { data, error } = await supabase
            .from('news_articles')
            .select('*')
            .order('created_at', { ascending: false })
            .range(from, to);

        if (error) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:red; padding:20px;">데이터를 불러오지 못했습니다: ${error.message}</td></tr>`;
            return;
        }

        if (!data || data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:20px;">수집된 뉴스가 없습니다.</td></tr>`;
            return;
        }

        tbody.innerHTML = data.map((item, i) => {
            const no = from + i + 1;
            const date = new Date(item.created_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
            return `
                <tr class="clickable-row" data-id="${item.id}">
                    <td style="color:#888;">${no}</td>
                    <td><b>${item.company_name || '알수없음'}</b></td>
                    <td style="text-align:left;">${item.title}</td>
                    <td>${item.source_name || '-'}</td>
                    <td style="color:#888; font-size:13px;">${date}</td>
                </tr>
            `;
        }).join('');

        // 행 클릭 이벤트 추가 (상세 모달)
        tbody.querySelectorAll('.clickable-row').forEach(row => {
            row.addEventListener('click', () => {
                const articleId = row.getAttribute('data-id');
                const article = data.find(a => a.id === articleId);
                if (article) showNewsDetail(article);
            });
        });

        // 하단 페이지 번호 그리기
        renderPagination('pagination-container', currentPage, totalCount, PAGE_SIZE, (p) => loadPage(p));
    }

    // 첫 페이지 호출
    loadPage(0);
}

// 뉴스 상세 팝업창을 보여주는 함수
function showNewsDetail(article) {
    const modal = document.getElementById('news-modal');
    const title = document.getElementById('news-modal-title');
    const body = document.getElementById('news-modal-body');
    const link = document.getElementById('news-modal-link');
    
    // 제목 및 링크 설정
    title.innerText = article.title;
    link.href = article.source_url || '#';
    
    // 본문 구성 (이미지가 있으면 위쪽에 표시)
    let bodyHtml = '';
    if (article.thumbnail_url) {
        bodyHtml += `
            <div style="text-align:center; margin-bottom:15px;">
                <img src="${article.thumbnail_url}" style="max-width:100%; border-radius:8px; border:1px solid #eee;">
            </div>
        `;
    }
    
    bodyHtml += `
        <div style="background:#f9f9f9; padding:15px; border-radius:8px; line-height:1.6; color:#444;">
            <p style="margin-top:0;"><b>출처:</b> ${article.source_name || '알 수 없음'}</p>
            <hr style="border:0; border-top:1px solid #eee; margin:15px 0;">
            <div style="white-space:pre-wrap;">${article.snippet || article.content || '본문 내용이 없습니다.'}</div>
        </div>
        <p style="font-size:12px; color:#999; margin-top:15px;">※ 본 요약 내용은 수집 당시의 데이터이며, 자세한 내용은 원문 기사를 확인해 주세요.</p>
    `;
    
    body.innerHTML = bodyHtml;
    
    // 모달 표시
    modal.style.display = 'flex';
    
    // 모달 닫기 이벤트들
    const closeBtns = [
        document.getElementById('close-news-modal-x'),
        document.getElementById('close-news-modal-btn')
    ];
    
    const hideModal = () => { modal.style.display = 'none'; };
    closeBtns.forEach(btn => {
        if (btn) btn.onclick = hideModal;
    });
}
