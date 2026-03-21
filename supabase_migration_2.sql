-- ==========================================
-- [Supabase DB 마이그레이션 적용 쿼리 2탄]
-- 관심 기업의 상세 정보 이력을 분리하고, 새로운 데이터를 저장하기 위한 쿼리입니다.
-- Supabase 대시보드의 SQL Editor에 복사 후 'Run'을 클릭하여 실행해주세요.
-- ==========================================

-- 1. companies 테이블 구조 변경
-- 기존에 있던 매일 변동되는 정보(marcap, per, pbr 등)는 company_histories 로 이동시킬 것입니다.
-- 다만 기존 데이터를 유지하기 위해 컬럼 삭제는 하지 않고, [사업 요약] 필드만 새로 추가합니다.
ALTER TABLE companies 
    ADD COLUMN IF NOT EXISTS business_summary TEXT,   -- 회사 (사업) 요약
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(); -- (혹시 등록날짜 컬럼이 없다면 추가)

-- 2. 매일 변하는 정보를 따로 기록하는 company_histories(이력) 테이블 생성
-- 매 배치가 돌 때마다 (가격, 기대수익률, 기업가치 등) 변동 내역이 이곳에 누적 저장됩니다.
CREATE TABLE IF NOT EXISTS company_histories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    price NUMERIC,                             -- 현재가
    change_rate NUMERIC,                       -- 등락률
    rvol NUMERIC,                              -- 거래량 급증 비율 (Relative Volume)
    marcap BIGINT,                             -- 시가총액
    per NUMERIC,                               -- 주가수익비율 (PER)
    pbr NUMERIC,                               -- 주가순자산비율 (PBR)
    annual_price_change NUMERIC,               -- 연간 가격 변화 (52주 변동률 %)
    expected_return NUMERIC,                   -- 기대 수익률 (애널리스트 목표가 대비 %)
    enterprise_value BIGINT,                   -- 현재 기업 가치 (EV)
    recorded_at TIMESTAMPTZ DEFAULT NOW()      -- 기록 일시
);

-- (선택) 조회를 빠르게 하기 위한 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_company_histories_company_id ON company_histories(company_id);
