let currentPage = 0;
const PAGE_SIZE = 15;
let isEndOfData = false;

export async function renderSubscriberList(contentEl, supabaseClient) {
    currentPage = 0;
    isEndOfData = false;

    contentEl.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Subscribers (구독자 관리)</h1>
            <p class="page-desc">아침 6시 주식 뉴스레터를 받는 사람들의 정보입니다.</p>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th style="width: 40%">이메일 주소 (Email Address)</th>
                        <th style="width: 30%">구독 상태 (Status)</th>
                        <th style="width: 30%">가입 날짜 (Joined Date)</th>
                    </tr>
                </thead>
                <tbody id="subscriber-list-body">
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

    await fetchAndRenderData(supabaseClient);
}

async function fetchAndRenderData(supabaseClient) {
    if (isEndOfData) return;
    
    const btn = document.getElementById('load-more-btn');
    btn.innerText = "불러오는 중...";
    btn.disabled = true;

    try {
        const { data, error } = await supabaseClient
            .from('subscribers')
            .select('*')
            .order('created_at', { ascending: false })
            .range(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE - 1);

        if (error) throw error;

        const tbody = document.getElementById('subscriber-list-body');

        if (data && data.length > 0) {
            data.forEach(row => {
                const tr = document.createElement('tr');
                const dateText = new Date(row.created_at).toLocaleDateString('ko-KR', { timeZone: 'Asia/Seoul' });
                tr.innerHTML = `
                    <td style="font-weight:600">${row.email}</td>
                    <td>Active (활성)</td>
                    <td style="color:var(--text-muted)">${dateText}</td>
                `;
                tbody.appendChild(tr);
            });

            currentPage++;

            if (data.length < PAGE_SIZE) {
                isEndOfData = true;
                btn.style.display = 'none';
            }
        } else {
            isEndOfData = true;
            btn.style.display = 'none';
            if (currentPage === 0) {
                tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;">현재 구독자가 없습니다.</td></tr>';
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
