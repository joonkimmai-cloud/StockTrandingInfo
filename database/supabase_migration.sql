-- ==========================================
-- [Supabase DB 마이그레이션 적용 쿼리]
-- SerpApi 도입으로 인해 추가된 뉴스 관련 필드들을 생성하는 쿼리입니다.
-- Supabase 대시보드의 SQL Editor에 복사 후 'Run'을 클릭하여 실행해주세요.
-- ==========================================

-- news_articles 테이블에 새로운 컬럼(열) 4개 추가하기
ALTER TABLE news_articles 
    ADD COLUMN IF NOT EXISTS thumbnail_url TEXT,     -- 썸네일 이미지 링크
    ADD COLUMN IF NOT EXISTS snippet TEXT,           -- 뉴스 기사 요약본 (미리보기 텍스트)
    ADD COLUMN IF NOT EXISTS source_name TEXT,       -- 작성 언론사 이름 (예: 한경비즈니스)
    ADD COLUMN IF NOT EXISTS position INTEGER;       -- 검색 결과 내 노출 순위 (1, 2, 3...)

-- (선택) 만약 이전에 수집한 데이터와 충돌을 최소화하거나 
-- 중복 등록을 방지하려면 아래처럼 company_id와 title에 Unique 제약 조건을 추가할 수 있습니다.
-- ALTER TABLE news_articles ADD CONSTRAINT unique_news_title UNIQUE (company_id, title);
