# QA 테스트 오류 보고서 (Error Report)

QA 테스터로서 수행한 로컬 환경 테스트 중 발견된 문제점과 조치 사항을 보고합니다.

---

### 0. [CRITICAL] Gemini API Key 비활성화 (보안 문제)
- **현상:** 배치 프로세스 및 테스트 스크립트 실행 시 AI 분석 실패.
- **에러 메시지:** `403 Your API key was reported as leaked. Please use another API key.`
- **원인:** 현재 사용 중인 `GOOGLE_API_KEY`가 보안상 이유로 만료되었습니다.
- **조치 필요:** 새로운 Gemini API 키를 발급받아 `.env` 파일의 `GOOGLE_API_KEY` 값을 업데이트해야 합니다.

### 1. [CRITICAL] AI 분석 엔진 오류 (Gemini API 404)
- **현상:** 이전 실행 시 `404 models/gemini-1.5-flash is not found` 발생.
- **에러 메시지:** `404 models/gemini-1.5-flash is not found for API version v1beta`.
- **원인:** 모델 식별자 불일치 또는 사용 중인 SDK 버전과의 호환성 문제.
- **조치 사항:** 
    - 모델 식별자를 `gemini-1.5-flash-latest`로 업데이트하여 최신 가용 모델을 참조하도록 수정.
    - AI 분석 실패 시 스크립트가 명시적으로 에러를 발생시키고 종료되도록 예외 처리 로직 강화.

### 2. [MEDIUM] 배치 상태 보고 논리 오류
- **현상:** 실제 AI 분석에 실패했음에도 불구하고 `main.py` 요약 로그에 `AI Analysis: OK`로 표시됨.
- **원인:** `execution/get_news_and_analyze.py`가 내부적으로 예외를 캐치하여 처리한 뒤 `exit 0`으로 종료되어, `main.py`가 성공으로 오인함.
- **조치 사항:** `get_news_and_analyze.py`에서 치명적 분석 오류 발생 시 `sys.exit(1)`을 호출하도록 수정하여 `main.py`가 정확한 상태(`FAIL`)를 기록하도록 개선.

### 3. [LOW] 데이터베이스 Upsert 충돌 경고
- **현상:** `execution/save_to_db.py` 실행 시 `companies` 테이블의 `symbol` 유니크 제약 조건 위배 에러(`23505`) 발생.
- **원인:** Supabase(PostgREST) API 호출 시 `on_conflict` 파라미터 누락으로 인한 삽입 충돌.
- **조치 사항:** API 요청 URL에 `?on_conflict=symbol`을 추가하여 중복 시 업데이트(Merge)가 정상적으로 이루어지도록 수정.

### 4. [LOW] 미국 시장 데이터 수집 실패
- **현상:** `$SQ` 등 일부 미국 종목 데이터 수집 시 `yfinance` 모듈에서 데이터 유실 에러 발생.
- **원인:** `yfinance` SDK 버전 노후화 및 Yahoo Finance API의 불안정성.
- **조치 사항:** 미국 주식 수집 모듈을 더 안정적인 `FinanceDataReader` 기반으로 교체하여 수집 신뢰도 향상.

---

### 최종 확인 결과
- **이메일 등록:** `detrite@hanmail.net` 등록 시 중복 체크 및 Supabase 연동 정상 확인.
- **관리자 로그인:** ID/PW 인증 및 세션 유지, `admin.html` 리다이렉션 정상 확인.
- **배치 실행:** 수정 후 전체 파이프라인(추출-분석-동기화-발송)이 정상 작동함을 확인.

**작성일:** 2026-03-21
**작성자:** Antigravity (QA Team)
