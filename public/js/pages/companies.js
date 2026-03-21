let currentPage = 0;
const PAGE_SIZE = 15;
let isEndOfData = false;

export async function renderCompanies(contentEl, supabaseClient) {
    currentPage = 0;
    isEndOfData = false;

    contentEl.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Collected Companies (수집된 주식 시장 회사들)</h1>
            <p class="page-desc">현재 우리 시스템이 예의주시하며 수집 중인 기업들의 목록 및 주요 수치입니다.</p>
        </div>
        <div class="card">
            <table class="data-table">
                <thead>
                    <tr>
                        <th style="width: 20%">종목코드 (Symbol)</th>
                        <th style="width: 30%">회사명 (Name)</th>
                        <th style="width: 30%">시가총액 (Marcap)</th>
                        <th style="width: 20%">PER / PBR</th>
                    </tr>
                </thead>
                <tbody id="company-list-body">
                </tbody>
            </table>
            <div style="text-align: center; margin-top: 15px; padding: 10px;">
                <button id="load-more-btn" class="btn-blue" style="width: 200px;">더 보기 (Load More)</button>
            </div>
        </div>
    `;

    document.getElementById('load-more-btn').addEventListener('click', async () => {
        await fetchAndRenderData(supabaseClient);
    });

    // 1페이지 로드
    await fetchAndRenderData(supabaseClient);
}

async function fetchAndRenderData(supabaseClient) {
    if (isEndOfData) return;
    
    const btn = document.getElementById('load-more-btn');
    btn.innerText = "불러오는 중...";
    btn.disabled = true;

    try {
        const { data, error } = await supabaseClient
            .from('companies')
            .select('*')
            .order('marcap', { ascending: false })
            .range(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE - 1);

        if (error) throw error;

        const tbody = document.getElementById('company-list-body');

        if (data && data.length > 0) {
            data.forEach(row => {
                const tr = document.createElement('tr');
                const marcapText = row.marcap ? (row.marcap / 100000000).toFixed(1) + '억 원' : '-';
                tr.innerHTML = `
                    <td><b>${row.symbol}</b></td>
                    <td>${row.name}</td>
                    <td style="color:var(--primary-blue)">${marcapText}</td>
                    <td>${row.per || '-'}/${row.pbr || '-'}</td>
                `;
                tbody.appendChild(tr);
            });

            currentPage++;

            // 만약 가져온 갯수가 15개 미만이면 더 이상 데이터가 없는 것
            if (data.length < PAGE_SIZE) {
                isEndOfData = true;
                btn.style.display = 'none';
            }
        } else {
            isEndOfData = true;
            btn.style.display = 'none';
            if (currentPage === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">수집된 데이터가 없습니다.</td></tr>';
            }
        }
    } catch (err) {
        console.error("데이터 로드 중 에러:", err);
        alert("데이터를 가져오는 중 오류가 발생했습니다.");
    } finally {
        btn.innerText = "더 보기 (Load More)";
        btn.disabled = false;
    }
}
