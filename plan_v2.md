# 장중 뉴스 수집 배치 추가 기획서 (plan_v2.md)

## 1. 개요
사용자 요청에 따라 전일(또는 가장 최근) 수집된 관심 기업들을 대상으로, 지정된 시간(오전 9시, 12시, 오후 3시, 오후 5시)마다 최신 뉴스를 2건씩 추가 수집하여 DB에 저장하는 장중 배치를 구성합니다.

## 2. 요구사항 분석
* **대상 기업:** 전일(가장 최근 배치 기준) 수집된 회사 목록. DB의 `market_reports`와 `stock_analysis` 또는 `company_histories` 테이블을 조회하여 최신 기준으로 타겟 종목을 추출합니다.
* **수집 스케줄:** 09:00, 12:00, 15:00, 17:00 (KST 기준)
  * Github Actions의 Cron 표현식 (UTC 기준): `0 0,3,6,8 * * *`
* **수집 데이터:** 각 기업당 최신 뉴스 2건.
* **저장 위치:** Supabase의 `news_articles` 테이블에 누적 저장.

## 3. 설계 로직
### 3.1 신규 스크립트 작성 (`execution/intraday_news_batch.py`)
1. **대상 종목 추출:** Supabase REST API를 이용해 가장 최근(최대 1일 전) 저장된 `company_histories` 또는 `stock_analysis` 데이터를 기반으로 수집 대상 `company_id` 및 `symbol`, `name` 목록을 가져옵니다.
2. **뉴스 실시간 수집:** 기존 `get_news.py`의 `fetch_news_kr` 및 `fetch_news_us` 함수를 재활용하여 실시간 뉴스를 가져오되, 결과물을 상위 2개로 제한(Slice)합니다.
3. **DB 저장:** 기존에 저장된 뉴스와 중복되지 않도록 `news_articles` 테이블에 `title` 또는 `source_url` 기준으로 필터링한 후 Insert 합니다. (또는 무조건 Insert하되 프론트에서 최신순 노출)

### 3.2 Github Action Workflow 작성 (`.github/workflows/intraday_news_batch.yml`)
* `schedule` 트리거를 사용하여 정해진 KST 시간(UTC 00, 03, 06, 08시)마다 `intraday_news_batch.py`를 실행하도록 yml 배포 스크립트를 작성합니다.
* 기존 `daily_report.yml`에 있는 환경변수(Secrets)를 동일하게 물려받습니다.

## 4. 진행 순서
1. `execution/intraday_news_batch.py` 파이썬 코드 구현
2. `.github/workflows/intraday_news_batch.yml` CI/CD 파이프라인(배치) 등록
3. 수동 Trigger를 통한 배치 정상 동작 및 DB(`news_articles`) 적재 테스트 확인

---
위 기획 내용에 대해 검토해 주시고, 승인해주시면 즉시 구현에 착수하겠습니다.
