import { renderPagination } from './pagination.js';

const PAGE_SIZE = 15;

export async function renderCompanies(contentEl, supabaseClient) {
    let currentPage = 0;
    let currentQuery = '';

    contentEl.innerHTML = `
        <div class="page-header" style="display:flex; justify-content:space-between; align-items:flex-end;">
            <div>
                <h1 class="page-title">Collected Companies</h1>
                <p class="page-desc" id="total-count-desc">수집된 기업 목록입니다.</p>
            </div>
            <div class="page-header-actions">
                <div class="search-container">
                    <input type="text" id="company-search-input" class="search-input" placeholder="심볼, 기업명, 업종 검색...">
                    <button id="company-search-btn" class="search-btn">🔍</button>
                </div>
            </div>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th class="col-no">#</th>
                        <th style="width: 15%">종목코드 (Symbol)</th>
                        <th style="width: 22%">회사명 (Name)</th>
                        <th style="width: 20%">시가총액 (Marcap)</th>
                        <th style="width: 15%">PER / PBR</th>
                        <th style="width: 14%">등록일자</th>
                        <th style="width: 14%">업데이트</th>
                    </tr>
                </thead>
                <tbody id="list-body"></tbody>
            </table>
            <div id="pagination-container"></div>
        </div>
    `;

    async function loadPage(page, query = currentQuery) {
        currentPage = page;
        currentQuery = query;
        const from = page * PAGE_SIZE;
        const to = from + PAGE_SIZE - 1;

        const tbody = document.getElementById('list-body');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:30px;">불러오는 중...</td></tr>';

        let q = supabaseClient.from('companies').select('*', { count: 'exact' });
        
        if (query) {
            q = q.or(`symbol.ilike.*${query}*,name.ilike.*${query}*,sector.ilike.*${query}*,industry.ilike.*${query}*`);
        }

        const { data, count, error } = await q
            .order('updated_at', { ascending: false })
            .range(from, to);

        if (error) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:30px; color:red;">에러: ${error.message}</td></tr>`;
            return;
        }

        const totalCount = count || 0;
        document.getElementById('total-count-desc').innerText = `수집된 기업 목록입니다. (총 ${totalCount}개${query ? ' 검색됨' : ''})`;

        if (data && data.length > 0) {
            tbody.innerHTML = data.map((row, i) => {
                const no = from + i + 1;
                const marcap = row.marcap ? (row.marcap / 100000000).toFixed(1) + '억 원' : '-';
                const dateCreated = row.created_at ? new Date(row.created_at).toLocaleDateString('ko-KR') : '-';
                const dateUpdated = row.updated_at ? new Date(row.updated_at).toLocaleDateString('ko-KR') : '-';
                
                return `<tr class="clickable-row" onclick="window.showCompanyDetail('${row.id}')">
                    <td class="col-no">${no}</td>
                    <td><b>${row.symbol}</b></td>
                    <td>${row.name}</td>
                    <td style="color:var(--primary-blue)">${marcap}</td>
                    <td>${row.per || '-'}/${row.pbr || '-'}</td>
                    <td style="font-size: 0.8rem; color: #666;">${dateCreated}</td>
                    <td style="font-size: 0.8rem; color: #666;">${dateUpdated}</td>
                </tr>`;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:30px;">결과가 없습니다.</td></tr>';
        }

        renderPagination('pagination-container', currentPage, totalCount, PAGE_SIZE, (p) => loadPage(p, currentQuery));
    }

    // 검색 이벤트 바인딩
    const searchInput = document.getElementById('company-search-input');
    const searchBtn = document.getElementById('company-search-btn');

    const handleSearch = () => {
        loadPage(0, searchInput.value.trim());
    };

    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });

    await loadPage(0);

    // 전역 함수로 등록 (상세보기 모달)
    window.showCompanyDetail = async (id) => {
        const { data, error } = await supabaseClient.from('companies').select('*').eq('id', id).single();
        if (error || !data) {
            alert('데이터를 가져오는데 실패했습니다.');
            return;
        }

        const modal = document.getElementById('company-modal');
        const body = document.getElementById('company-modal-body');
        const title = document.getElementById('company-modal-title');

        title.innerText = `${data.name} (${data.symbol})`;
        
        // 시가총액/매출/순이익 단위 변환 (단위: 억)
        const formatBillion = (val) => val ? (val / 100000000).toLocaleString(undefined, {maximumFractionDigits:1}) + '억' : '-';
        const marcap = formatBillion(data.marcap);
        const revenue = formatBillion(data.revenue);
        const netIncome = formatBillion(data.net_income);
        const margin = data.operating_margins ? (data.operating_margins * 100).toFixed(2) + '%' : '-';

        body.innerHTML = `
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 20px; border-radius: 8px; margin-bottom: 24px;">
                <h4 style="margin: 0 0 12px 0; color: #0051C3; display: flex; align-items: center; gap: 8px; font-size: 1.1rem;">
                    <span>🏢</span> 기업 개요
                </h4>
                <p style="font-size: 0.95rem; line-height: 1.7; color: #334155; margin: 0; white-space: pre-wrap;">${data.business_summary || '수집된 기업 요약 정보가 없습니다.'}</p>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 20px;">
                <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <h4 style="margin: 0 0 16px 0; color: #111827; border-left: 4px solid #0051C3; padding-left: 10px; font-size: 1rem;">🔎 기본 정보</h4>
                    <table style="width: 100%; font-size: 0.95rem; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 10px 0; color: #6b7280; width: 40%;">시장 구분</td><td style="font-weight: 500;">${data.market || '-'}</td></tr>
                        <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 10px 0; color: #6b7280;">섹터 / 업종</td><td style="font-weight: 500;">${data.sector || '-'}</td></tr>
                        <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 10px 0; color: #6b7280;">상세 산업</td><td style="font-weight: 500;">${data.industry || '-'}</td></tr>
                        <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 10px 0; color: #6b7280;">대표자 (CEO)</td><td style="font-weight: 500;">${data.ceo || '-'}</td></tr>
                        <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 10px 0; color: #6b7280;">설립 / 상장일</td><td style="font-weight: 500;">${data.founded_date || '-'} / ${data.listing_date || '-'}</td></tr>
                        <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 10px 0; color: #6b7280;">위치 (City)</td><td style="font-weight: 500;">${data.city || '-'}</td></tr>
                        <tr><td style="padding: 10px 0; color: #6b7280;">공식 웹사이트</td><td><a href="${data.website}" target="_blank" style="color: #0051C3; text-decoration: none;">${data.website ? '방문하기 🔗' : '-'}</a></td></tr>
                    </table>
                </div>
                
                <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <h4 style="margin: 0 0 16px 0; color: #111827; border-left: 4px solid #238636; padding-left: 10px; font-size: 1rem;">💵 주요 재무 및 지표</h4>
                    <table style="width: 100%; font-size: 0.95rem; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 10px 0; color: #6b7280; width: 40%;">시가총액</td><td style="font-weight: 600;">${marcap}</td></tr>
                        <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 10px 0; color: #6b7280;">연간 매출액</td><td style="font-weight: 600;">${revenue}</td></tr>
                        <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 10px 0; color: #6b7280;">영업이익률</td><td style="color: #238636; font-weight: 600;">${margin}</td></tr>
                        <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 10px 0; color: #6b7280;">당기순이익</td><td style="font-weight: 600;">${netIncome}</td></tr>
                        <tr><td style="padding: 10px 0; color: #6b7280;">PER / PBR</td><td style="font-weight: 600;">${data.per || '-'} / ${data.pbr || '-'}</td></tr>
                    </table>
                </div>
            </div>
        `;

        modal.style.display = 'flex';

        // 모달 닫기 이벤트들
        const closeBtns = [
            document.getElementById('close-company-modal-x'),
            document.getElementById('close-company-modal-btn')
        ];
        
        const hideModal = () => { modal.style.display = 'none'; };
        closeBtns.forEach(btn => {
            if (btn) btn.onclick = hideModal;
        });

        // 뒷 배경 클릭 시 닫기
        modal.onclick = (e) => {
            if (e.target === modal) hideModal();
        };
    };
}
