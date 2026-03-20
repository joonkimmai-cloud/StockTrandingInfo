// ==========================================
// 관리자 페이지 메인 Javascript 로직
// 여러 페이지로 나누어진 기능(함수)들을 가져와서 전체 화면을 조작합니다.
// ==========================================

// 다른 파일(페이지)에 쪼개둔 화면 그리는 함수들을 가져오기 (import)
import { renderBatchSummary } from './pages/batch-summary.js';
import { renderExecutionLogs } from './pages/execution-logs.js';
import { renderCompanies } from './pages/companies.js';
import { renderSubscriberList } from './pages/subscriber-list.js';

// ------------------------------------------
// 1. 보안 체크 및 기본 설정 (Supabase 등)
// ------------------------------------------

// 관리자인지 로그인 기록을 확인. (SessionStorage에 정보가 없다면 튕겨냄)
if (sessionStorage.getItem('isAdmin') !== 'true') { 
    window.location.href = 'login.html'; 
}

// 로그아웃을 처리하는 함수를 누구나 쓸 수 있게 전역(window) 공간에 만듭니다.
window.handleLogout = () => {
    sessionStorage.clear(); // 로그인 정보 모두 지움
    window.location.href = 'login.html'; // 다시 로그인 화면으로!
};

// Supabase (백엔드/데이터베이스 서버) 정보
const SUPABASE_URL = "https://fwptckxvhyzydrfralhw.supabase.co";
const SUPABASE_KEY = "sb_publishable_ZRdywELTvsTlfdU4SUCYsg_IASTgk3X";
const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

// 사용자가 보고 있는 현재 '페이지 이름'을 저장하는 변수
let currentPageId = 'batch-summary'; 

// ------------------------------------------
// 2. 초기 셋팅 (버튼 클릭과 연결하기 등)
// ------------------------------------------
// HTML이 준비되면 아래 코드들을 실행시킵니다.
document.addEventListener('DOMContentLoaded', () => {

    // [좌측 메뉴] 각 글자나 버튼을 클릭했을 때 화면이 바뀌도록 '클릭 이벤트'를 달아줍니다.
    // navTo() 라는 함수에 (아이디, 그룹이름) 두 개의 정보를 보냅니다.
    document.getElementById('nav-batch-summary').addEventListener('click', () => navTo('batch-summary', 'Monitoring'));
    document.getElementById('nav-execution-logs').addEventListener('click', () => navTo('execution-logs', 'Monitoring'));
    document.getElementById('nav-companies').addEventListener('click', () => navTo('companies', 'Data Management'));
    document.getElementById('nav-subscriber-list').addEventListener('click', () => navTo('subscriber-list', 'Subscribers'));
    
    // [단축 팝업창 (모달)] 닫고, 열고, 시작하는 것들에 대한 클릭 연결
    document.getElementById('close-modal-x').addEventListener('click', window.closeModal);
    document.getElementById('modal-ok-btn').addEventListener('click', window.closeModal);
    document.getElementById('modal-start-btn').addEventListener('click', window.executeBatchAPI);

    // 로그아웃 버튼
    document.getElementById('logout-btn').addEventListener('click', window.handleLogout);

    // 맨 처음 화면이 열릴 때 전체 통계를 한 번 불러옵니다.
    initDashboard();
});

// ------------------------------------------
// 3. 네비게이션 동작 (화면 이동) 함수
// ------------------------------------------
function navTo(pageId, groupName) {
    currentPageId = pageId;
    
    // 상단 네비게이터의 글씨 (어느 그룹 안에 있는지) 바꾸기. ex) Monitoring
    document.getElementById('nav-path').innerText = groupName;
    
    // 왼쪽 메뉴에서 선택된 버튼만 파란색(active)으로 하이라이트를 주고 나머지는 뺌.
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.remove('active');
        if (item.id === `nav-${pageId}`) item.classList.add('active');
    });
    
    // 실제 해당 페이지 화면 그리기 호출
    loadPage(pageId);
}

// 각 종류별 화면을 그리는 메인 로직. 아이디(pageId)에 따라 다르게 가져옴!
export async function loadPage(pageId) {
    // 뼈대를 넣을 빈 상자(main-content)를 만듭니다.
    const contentEl = document.getElementById('main-content');
    
    // 데이터를 다 가져오기 전까지 사용자에게 돌고 있는 로딩 표시자를 보여줍니다.
    contentEl.innerHTML = `<div style="padding: 40px; text-align: center;"><div class="loader"></div> 데이터를 불러오는 중입니다...</div>`;

    // 어떤 화면 아이디인지 확인하고 알맞은 '렌더링 함수(불러온 파일 안에 있음)'를 실행.
    if (pageId === 'batch-summary') {
        await renderBatchSummary(contentEl, supabaseClient);
    } else if (pageId === 'execution-logs') {
        await renderExecutionLogs(contentEl, supabaseClient);
    } else if (pageId === 'companies') {
        await renderCompanies(contentEl, supabaseClient);
    } else if (pageId === 'subscriber-list') {
        await renderSubscriberList(contentEl, supabaseClient);
    }
}

// ------------------------------------------
// 4. 전역(Global) 공간에 저장해야 하는 함수들
// (모달창과 API 연동을 다루는 복잡한 함수들입니다.)
// ------------------------------------------

// 모달(팝업창)을 열고 현재까지 저장된 전체 배치의 과거 로그(기록)를 보여주기
window.showPastLog = function(base64Log, status) {
    const modal = document.getElementById('batch-modal');
    const logWin = document.getElementById('modal-log-window');
    const statusText = document.getElementById('modal-status-text');
    const startBtn = document.getElementById('modal-start-btn');
    const okBtn = document.getElementById('modal-ok-btn');
    const closeBtn = document.getElementById('close-modal-x');

    // 1. 암호화된(Base64) 텍스트를 한글이 깨지지 않게 변환(디코딩)
    const logContent = decodeURIComponent(escape(atob(base64Log)));

    // 2. 모달창 화면에 띄우기
    modal.style.display = 'flex';
    logWin.innerHTML = logContent;
    statusText.innerText = '과거 실행 기록 (' + status + ')';
    
    // 성공/실패 여부에 따라 텍스트 색 변경
    if(status === 'SUCCESS' || status === 'COMPLETED'){
        statusText.style.color = 'var(--success-color)'; // 초록색
    } else if(status && status.toLowerCase().indexOf('error') !== -1) {
        statusText.style.color = 'var(--error-color)'; // 빨간색
    } else {
        statusText.style.color = 'var(--text-dark)'; // 기본 색
    }

    // 팝업 하단 버튼 정리 (새로 실행할게 아니므로 Start 버튼 숨김)
    startBtn.style.display = 'none';
    okBtn.style.display = 'inline-block';
    okBtn.innerText = '닫기'; // Close 버튼
    closeBtn.style.display = 'inline-block';
};

// "배치 실행" 버튼을 누르자마자 뜨는 모달창 준비 함수 (아직 실제 실행 전)
window.handleRunBatch = async function() {
    const modal = document.getElementById('batch-modal');
    const logWin = document.getElementById('modal-log-window');
    const statusText = document.getElementById('modal-status-text');
    const startBtn = document.getElementById('modal-start-btn');
    const okBtn = document.getElementById('modal-ok-btn');
    const closeBtn = document.getElementById('close-modal-x');

    modal.style.display = 'flex'; // 모달창 열기
    logWin.innerHTML = '> 사용자가 실행 버튼을 누르기를 대기 중입니다...\n'; // 터미널 형태의 글씨 삽입
    statusText.innerText = '준비 완료 (Ready to Start)';
    statusText.style.color = 'var(--text-muted)'; // 회색
    
    // 실행 화면이므로 Start 버튼을 보여줌
    startBtn.style.display = 'inline-block';
    okBtn.style.display = 'none';
    closeBtn.style.display = 'inline-block';
};

// 팝업창에서 진짜 녹색 "실행" 버튼을 눌렀을 때 백엔드에 API 요청을 보냄
window.executeBatchAPI = async function() {
    const logWin = document.getElementById('modal-log-window');
    const statusText = document.getElementById('modal-status-text');
    const startBtn = document.getElementById('modal-start-btn');
    const closeBtn = document.getElementById('close-modal-x');
    const okBtn = document.getElementById('modal-ok-btn');

    // 눌렀으니 두번 못 누르게 숨김
    startBtn.style.display = 'none';
    closeBtn.style.display = 'none';
    logWin.innerHTML = '> 배치를 시작해달라는 요청을 시스템에 보냈습니다...\n';
    statusText.innerText = '작업을 진행하고 있습니다...';
    statusText.style.color = 'var(--primary-blue)'; // 파란색 표시

    try {
        // 백엔드 파이썬(Python) 서버에 POST(실행) 신호 보내기
        const response = await fetch('http://localhost:5000/run-batch', { method: 'POST' });
        const result = await response.json();
        
        logWin.innerHTML += '> ' + result.message + '\n';
        // 바로 상태 확인 모드로 돌입 (주기적으로 서버에 물어보기 시작!)
        window.pollBatchStatus();
    } catch (err) {
        logWin.innerHTML += `> ERROR: API 서버가 실행 중이지 않습니다. (웹 페이지가 아닌 파이썬 배치 서버가 켜져있는지 확인하세요.)\n`;
        statusText.innerText = '실행 실패 (서버 연결 불가)';
        statusText.style.color = 'var(--error-color)';
        
        // 닫기 버튼 열어주기
        okBtn.style.display = 'block';
        okBtn.innerText = '확인 후 닫기';
        closeBtn.style.display = 'block';
    }
};

// 진행되는 동안(status.is_running === true) 파이썬 서버한테 로그를 계속해서 물어보는 재귀 함수
window.pollBatchStatus = async function() {
    const logWin = document.getElementById('modal-log-window');
    const statusText = document.getElementById('modal-status-text');
    const okBtn = document.getElementById('modal-ok-btn');
    const closeBtn = document.getElementById('close-modal-x');

    try {
        const response = await fetch('http://localhost:5000/batch-status');
        const status = await response.json();

        // 파이썬 서버로부터 돌려받은 최신 실시간 로그들을 터미널 창에 업데이트
        if (status.logs) {
            logWin.textContent = status.logs;
            // 스크롤이 자동으로 계속 내려가도록 맞춰주는 역할입니다.
            logWin.scrollTop = logWin.scrollHeight;
        }

        // 서버쪽 답변이 '나는 아직 뛰는 중이야' 이면 -> 1.5초(1500) 뒤에 이 과정을 또 반복
        if (status.is_running) {
            statusText.innerText = '작업 진행 중... (Batch in Progress)';
            setTimeout(window.pollBatchStatus, 1500); 
        } else {
            // 끝났어! 인 경우
            const fullLog = status.last_output || status.logs;
            // 끝난 상태 중에서도 에러가 포함되어있는지에 따라 메시지와 컬러 차이를 줌
            if (fullLog && (fullLog.toLowerCase().includes('failed') || fullLog.toLowerCase().includes('error'))) {
                statusText.innerText = '에러와 함께 작업이 끝났습니다.';
                statusText.style.color = 'var(--error-color)'; // 붉은색
            } else {
                statusText.innerText = '성공적으로 작업이 완료되었습니다!';
                statusText.style.color = '#238636'; // 녹색
            }
            
            // 모든게 끝났으므로 모달창의 완료(닫기) 버튼을 활성화
            okBtn.style.display = 'block';
            okBtn.innerText = '닫기 및 화면고침';
            closeBtn.style.display = 'block';
        }
    } catch (err) {
        console.error("폴링에러 (주기적 서버상태 체크에 문제 발생):", err);
    }
};

// 바탕 화면 고요/로딩 끝날때 모달을 안 보이게 끄는 함수
window.closeModal = function() {
    document.getElementById('batch-modal').style.display = 'none';
    // 창을 닫으면 현재 보고 있던 화면을 최신 상위 데이터베이스를 기준으로 다시 그림.
    loadPage(currentPageId);
};

// (추가 기능) 팝업을 띄우지 않아도 백그라운드에 배치가 자동으로 뛰고 있는지 확인하는 함수.
window.checkBatchStatus = function() {
    fetch('http://localhost:5000/batch-status')
        .then(res => res.json())
        .then(status => {
            const btn = document.getElementById('run-batch-btn');
            if (btn) {
                if (status.is_running) {
                    btn.disabled = true; // 서버가 일하고 있으면 버튼을 회색으로 잠가버림
                    btn.innerText = '작업 진행 중...';
                } else {
                    btn.disabled = false; // 풀림
                    btn.innerText = '지금 배치 실행하기 (Run Batch Now)';
                }
            }
        }).catch(() => {});
};

// 관리자 화면 구동 초기화(맨 처음 시작점)
async function initDashboard() {
    // 1. 현재 테이블들에 정보가 몇개 있는지 데이터베이스에 카운팅해서 숫자로 가져오기
    try {
        const { count: subCount } = await supabaseClient.from('subscribers').select('*', { count: 'exact', head: true });
        const { count: compCount } = await supabaseClient.from('companies').select('*', { count: 'exact', head: true });
        if(document.getElementById('count-subscribers')) {
            document.getElementById('count-subscribers').innerText = subCount || 0;
        }
        if(document.getElementById('count-companies')) {
            document.getElementById('count-companies').innerText = compCount || 0;
        }
    } catch(e) { console.error('통계가져오기 실패', e); }
    
    // 2. 숫자를 다가져온 이후 현재 화면을 다시 로드(Batch Summary가 기본)
    loadPage('batch-summary');
}
