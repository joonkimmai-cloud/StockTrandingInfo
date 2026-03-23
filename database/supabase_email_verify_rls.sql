-- email_verifications 테이블의 RLS(행 수준 보안) 설정 및 익명 사용자(anon) 접근 허용 정책
-- 이 설정이 없으면 클라이언트(브라우저)에서 Supabase로 직접 INSERT/DELETE 할 때 401 Unauthorized 에러가 발생합니다.

ALTER TABLE email_verifications ENABLE ROW LEVEL SECURITY;

-- 1. Insert (새로운 인증 코드 저장) 허용
DROP POLICY IF EXISTS "Enable insert for anon" ON email_verifications;
CREATE POLICY "Enable insert for anon" ON email_verifications
    FOR INSERT
    WITH CHECK (true);

-- 2. Select (인증 코드 확인용) 허용
DROP POLICY IF EXISTS "Enable select for anon" ON email_verifications;
CREATE POLICY "Enable select for anon" ON email_verifications
    FOR SELECT
    USING (true);

-- 3. Delete (사용한 코드 삭제용) 허용
DROP POLICY IF EXISTS "Enable delete for anon" ON email_verifications;
CREATE POLICY "Enable delete for anon" ON email_verifications
    FOR DELETE
    USING (true);
