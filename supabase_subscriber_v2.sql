-- 1. 구독 상태 컬럼(is_active) 추가 (기본값 true)
ALTER TABLE public.subscribers ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

-- 2. 관리자 페이지(anon)에서 구독 상태를 업데이트할 수 있도록 RLS 정책 추가/수정
-- (주의: 실제 서비스에서는 보안을 위해 꼭 관리자 인증 토큰을 검사해야 합니다.)
DROP POLICY IF EXISTS "Allow anon update subscribers" ON public.subscribers;
CREATE POLICY "Allow anon update subscribers" ON public.subscribers
    FOR UPDATE
    USING (true)
    WITH CHECK (true);

-- 3. 확인용 로그
COMMENT ON COLUMN public.subscribers.is_active IS '구독 활성화 여부 (true: 활성, false: 중지)';
