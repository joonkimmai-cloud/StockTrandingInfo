-- 구독자 정보를 저장하기 위한 테이블 생성
CREATE TABLE public.subscribers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 보안: Row Level Security (RLS) 설정 (선택 사항)
-- 익명 사용자가 이메일을 추가할 수 있도록 허용
ALTER TABLE public.subscribers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public insert" ON public.subscribers
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow service_role full access" ON public.subscribers
    FOR ALL USING (true);
