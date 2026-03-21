/* 
   login.js
   관리자 ID(이메일)와 비밀번호를 입력받고 데이터베이스(Supabase)에 접근하여
   진짜 관리자가 맞는지 로그인 여부를 확인하는 자바스크립트 로직입니다. 
*/

// 1. Supabase 접속 주소 및 '공개' 연결고리 비밀번호 (공용 키)
const SUPABASE_URL = "https://fwptckxvhyzydrfralhw.supabase.co";
const SUPABASE_KEY = "sb_publishable_ZRdywELTvsTlfdU4SUCYsg_IASTgk3X";

// 2. 앱(웹페이지)가 시작할 때 위 정보를 조합하여, supabaseClient라는 통신 객체를 새로 만듭니다.
const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

/**
 * 3. 관리자가 로그인 버튼을 클릭했을 때 작동하는 메인 함수
 * async : 이 함수 안에서 네트워크(DB) 통신 등 잠시 시간이 걸리는 동작(await)을 할 수 있게 허용합니다.
 */
async function handleLogin() {
    // 3-1. 사용자가 화면에 직접 입력한 이메일과 비밀번호 칸의 내용을 읽어 변수에 통에 담아 둡니다.
    const email = document.getElementById('admin-id').value;
    const password = document.getElementById('admin-pw').value;
    
    // 3-2. 오류 메시지 상자나, 버튼 안의 글자, 로딩 동그라미 같이 바꿔치기 할 화면 요소들을 불러옵니다.
    const errorEl = document.getElementById('error-msg');
    const btnText = document.getElementById('btn-text');
    const btnLoader = document.getElementById('btn-loader');
    const loginBtn = document.getElementById('login-btn');

    // 4. 아주 기초적인 에러 체크: 칸 중에 하나라도 텅 비어있다면 그냥 경고를 띄웁니다!
    if (!email || !password) {
        errorEl.style.display = 'block'; // 숨겨두었던 빨간 에러 메시지를 눈에 보이도록 변경 ('none' -> 'block')
        return; // 작업을 당장 여기서 정지합니다.
    }

    // 5. 서버에 물어보는 동안 잠깐 화면에 보여줄 눈속임 효과(UI Feedback) 
    // - 에러 상자 끄고 
    // - 버튼 글씨 지우고 
    // - 빙글빙글 도는 효과를 켭니다 (+버튼 비활성화)
    errorEl.style.display = 'none';
    btnText.style.display = 'none';
    btnLoader.style.display = 'block';
    loginBtn.disabled = true;

    try {
        // 6. 진짜로 Supabase 데이터베이스에 "이 이메일을 가진 사람 정보 좀 주세요!" 하고 요청합니다. 
        // from('admin_users') : 'admin_users' 이름표가 붙은 공간 안에서
        // select(...) : 이메일과, 암호화된 기호(비밀번호 해시)를 추출
        // eq(...) : 방금 타이핑한 이메일 값과 똑같은 행만 찾아서
        // single() : 딱 한 명만 무조건 뽑아주세요. (없는 사람이면 에러 발생)
        const { data, error } = await supabaseClient
            .from('admin_users')
            .select('email, password_hash')
            .eq('email', email)
            .single();

        // 관리자가 아니거나 전혀 엉뚱한 값이라 못 가져오면(에러 발생 시) 아래 예외처리로 이동합니다.
        if (error || !data) {
            throw new Error('데이터베이스에서 해당 유저를 찾을 수 없습니다.');
        }

        // 7. 비밀번호 검증 (bcrypt)
        // 주의: Python bcrypt는 $2b$ prefix를 생성하지만 브라우저용 bcryptjs는 $2a$만 지원합니다.
        // 따라서 DB에서 가져온 해시의 $2b$를 $2a$로 변환 후 비교합니다.
        const bCryptLib = (typeof dcodeIO !== 'undefined') ? dcodeIO.bcrypt : bcrypt;

        // $2b$ → $2a$ 변환 (Python↔JS bcrypt 호환성 처리)
        const normalizedHash = data.password_hash.replace(/^\$2b\$/, '$2a$');

        const isValid = bCryptLib.compareSync(password, normalizedHash);

        if (isValid) { // 암호가 완벽하게 맞다면 (True 였다면)
            
            // 8. 브라우저가 제공하는 단기 기억 장치(Session Storage)에 "난 관리자가 맞다"는 증표와 계정 이벤트를 살짝 저장합니다.
            // (나중에 다른 화면에서 이 증거를 보고 "어? 관리자님이셨네요" 하고 통과시켜주기 위함입니다.)
            sessionStorage.setItem('isAdmin', 'true');
            sessionStorage.setItem('adminEmail', email);
            
            // 9. 드디어 실제 관리자 페이지 화면(admin.html)으로 방문자를 순간 이동시킵니다!
            location.href = 'admin.html';
        } else {
            // 패스워드 틀림
            throw new Error('비밀번호가 일치하지 않습니다.');
        }

    } catch (err) {
        // 위에서 뭔가 중간에 throw나 에러가 나서 튕겼을 때 아래가 작동합니다.
        // 개발자를 위해 에러 메시지 흔적을 남기고 화면에 공통 빨간불 에러 문구를 표시합니다.
        console.error("로그인 시도 중 문제 발생: ", err);
        errorEl.style.display = 'block';
    } finally {
        // try에서 성공했든 에러로 터비든 어쨌든 빙글도는 버튼(로딩)을 원상 복구합니다!
        btnText.style.display = 'block';
        btnLoader.style.display = 'none';
        loginBtn.disabled = false;
    }
}
