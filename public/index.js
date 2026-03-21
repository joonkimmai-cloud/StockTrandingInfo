/* 
   index.js 
   메인 페이지에서 구독자 이메일을 받아 Supabase(데이터베이스)에 연결하고 
   정상적으로 등록되었는지 여부를 화면에 보여주는 중요한 스크립트입니다.
*/

// 1. Supabase 서버 주소와 공개(public) 접속 키. 
// 이 값들은 Supabase 대시보드에서 Project Settings -> API 메뉴에서 가져온 정보입니다.
const SUPABASE_URL = "https://fwptckxvhyzydrfralhw.supabase.co";
const SUPABASE_KEY = "sb_publishable_ZRdywELTvsTlfdU4SUCYsg_IASTgk3X";

let supabaseClient; // Supabase를 다루기 위한 "조종기" 역할을 하는 변수 하나 만들기

// 2. 페이지가 로드되면 즉시 Supabase 클라이언트를 초기화(설정) 합니다.
try {
    console.log("초기화 (Supabase Client 연결을 시도합니다...)");
    // supabase.createClient 함수를 이용해 서버가 연결된 클라이언트를 생성합니다.
    supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
    console.log("Supabase Client 연결 완료!");
} catch (e) {
    // 연결 실패 시 브라우저 콘솔창(F12)에 빨간색 에러 로그 출력
    console.error("Supabase 시작 오류 발생:", e);
}

/**
 * 3. 이메일을 구독하는 메인 동작 (Subscribe 버튼을 클릭할 때 실행)
 * async/await는 완료될 때까지 잠시 기다리라는 지시를 내리는 '비동기' 처리 방식입니다.
 */
async function subscribe() {
    console.log("사용자가 '무료 리포트 구독하기' 버튼을 클릭했습니다.");
    
    // HTML에 있는 입력창과 버튼 위치(ID)를 불러와 변수에 저장
    const emailInput = document.getElementById('email');    // 이메일 치는 칸
    const messageElement = document.getElementById('message'); // 에러/성공 글자 나오는 칸
    const btnText = document.getElementById('btnText');      // 구독하기 버튼 글씨
    
    // 입력창에 적힌 "실제 글자"를 가져옵니다.
    const email = emailInput.value;

    // 3-1. 이메일 형식(골뱅이 '@' 여부) 검증 단계
    if (!email || !email.includes('@')) {
        // 이메일이 아닌 것 같다면 빨간색 오류 메시지 표시(class="error" 적용) 후 중단(return)
        messageElement.innerHTML = '<span class="error">올바른 이메일 주소가 아닙니다. 다시 확인해 주세요.</span>';
        console.warn("이메일 형식 오류.");
        return; 
    }

    // 3-2. 올바른 주소라면 사용자에게 정말로 이 주소로 받을 거냐고 다시 물어보기
    const isConfirmed = confirm(`${email} 주소로 데일리 리포트를 구독 신청하시겠습니까?`);
    console.log("사용자 컨펌 유무:", isConfirmed);
    if (!isConfirmed) return; // '취소'를 누르면 그냥 여기서 종료

    try {
        // 3-3. 로딩 상태 표시 (사용자가 중복 터치하지 못하도록 하기 위함)
        btnText.innerText = "DB 처리 중...";
        btnText.disabled = true; // 버튼 비활성화 (클릭 방지)

        console.log("DB 검사: 이미 똑같은 이메일이 등록되어 있는지 확인 중...");
        
        // 데이터베이스(subscribers 테이블)에서 이 이메일이 있는지 하나만('single()') 찾아봅니다.
        const { data: existingUser, error: checkError } = await supabaseClient
            .from('subscribers')
            .select('email')
            .eq('email', email)
            .single();

        // existingUser(기존 회원) 값이 존재한다면, 이미 등록된 상태 (중복 가입 방지)
        if (existingUser) {
            alert(`${email} 주소는 이미 구독을 완료하신 주소입니다!`);
            messageElement.innerHTML = '<span class="success">이미 구독 중인 이메일입니다! 무료로 즐겨주세요.</span>';
            return; // 찾았으니 더이상 진행 안 하고 끝냄
        }

        // 3-4. 새로운 사람이라면 이제 테이블(subscribers)에 진짜로 넣기(insert) 
        console.log("등록: 새로운 구독자를 데이터베이스에 삽입합니다...");
        const { data, error } = await supabaseClient
            .from('subscribers')
            .insert([{ email }]); // [] 안의 {} 형태로 넣어야 합니다.

        // 만약 에러 값이 튀어나왔다면
        if (error) {
            console.error("데이터 삽입 에러 발생:", error);
            // 23505 코드는 Supabase(PostgreSQL)에서 "이미 있는 걸 또 넣으려고 해서 에러"라는 뜻입니다.
            if (error.code === '23505') {
                alert(`${email} 주소는 이미 구독 중입니다.`);
                messageElement.innerHTML = '<span class="success">이미 구독 중인 이메일입니다!</span>';
            } else {
                // 그 외 서버 오류일 경우
                messageElement.innerHTML = `<span class="error">서버 오류가 발생했습니다: ${error.message}</span>`;
            }
        // 저장에 성공했을 경우 (에러 값이 없다면)
        } else {
            console.log("성공! 데일리 리포트 구독자 항목에 추가됨.");
            messageElement.innerHTML = '<span class="success">🎉 구독 완료! 내일 아침부터 메일이 발송됩니다.</span>';
            emailInput.value = ''; // 입력창 텅 비워주기
        }

    } catch (err) {
        // 프로그램이 중간에 완전히 뻗어버린 치명적/알 수 없는 오류 처리
        console.error("구독 시스템 전체 오류:", err);
        messageElement.innerHTML = '<span class="error">시스템 치명적 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.</span>';
    } finally {
        // 상황이 긍정적이든 부정적이든 마지막엔 다시 버튼을 원상태로 돌리기(해제)
        btnText.innerText = "무료 리포트 구독하기";
        btnText.disabled = false;
    }
}
