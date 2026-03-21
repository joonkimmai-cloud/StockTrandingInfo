// ==========================================
// 공통 페이지네이션 UI 생성 헬퍼
// ==========================================
export function renderPagination(containerId, currentPage, totalCount, pageSize, onPageChange) {
    const totalPages = Math.ceil(totalCount / pageSize);
    if (totalPages <= 1) {
        const el = document.getElementById(containerId);
        if (el) el.innerHTML = '';
        return;
    }

    const container = document.getElementById(containerId);
    if (!container) return;

    let html = '<div class="pagination">';
    
    // 이전 버튼
    html += `<button class="page-btn ${currentPage === 0 ? 'disabled' : ''}" data-page="${currentPage - 1}" ${currentPage === 0 ? 'disabled' : ''}>&#8249;</button>`;
    
    // 페이지 번호 (최대 7개 표시)
    const maxVisible = 7;
    let startPage = Math.max(0, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages - 1, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) startPage = Math.max(0, endPage - maxVisible + 1);

    if (startPage > 0) {
        html += `<button class="page-btn" data-page="0">1</button>`;
        if (startPage > 1) html += `<span class="page-ellipsis">…</span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">${i + 1}</button>`;
    }

    if (endPage < totalPages - 1) {
        if (endPage < totalPages - 2) html += `<span class="page-ellipsis">…</span>`;
        html += `<button class="page-btn" data-page="${totalPages - 1}">${totalPages}</button>`;
    }

    // 다음 버튼
    html += `<button class="page-btn ${currentPage === totalPages - 1 ? 'disabled' : ''}" data-page="${currentPage + 1}" ${currentPage === totalPages - 1 ? 'disabled' : ''}>&#8250;</button>`;
    html += `<span class="page-info">총 ${totalCount}개 | ${currentPage + 1} / ${totalPages} 페이지</span>`;
    html += '</div>';

    container.innerHTML = html;

    // 클릭 이벤트
    container.querySelectorAll('.page-btn:not(.disabled)').forEach(btn => {
        btn.addEventListener('click', () => onPageChange(parseInt(btn.dataset.page)));
    });
}
