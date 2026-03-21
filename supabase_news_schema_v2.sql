-- 1. news_articles 테이블에 미보유 컬럼 추가
ALTER TABLE public.news_articles ADD COLUMN IF NOT EXISTS company_name TEXT;
ALTER TABLE public.news_articles ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;
ALTER TABLE public.news_articles ADD COLUMN IF NOT EXISTS snippet TEXT;
ALTER TABLE public.news_articles ADD COLUMN IF NOT EXISTS source_name TEXT;
ALTER TABLE public.news_articles ADD COLUMN IF NOT EXISTS position INTEGER;

-- 2. 기존 RLS 정책 정리 및 신규 조회 권한 부여
-- 관리자 페이지(익명 anon)에서 모든 뉴스를 볼 수 있도록 허용합니다.
DROP POLICY IF EXISTS "Allow anon select news" ON public.news_articles;
CREATE POLICY "Allow anon select news" ON public.news_articles
    FOR SELECT
    USING (true);

-- 확인용 로그
COMMENT ON COLUMN public.news_articles.company_name IS '기업 한글/영문 이름';
COMMENT ON COLUMN public.news_articles.snippet IS '기사 요약 내용 (본문 대신)';
