# 시큐어코딩 가이드 및 적용 결과 (StockTradingTop10)

본 문서는 소프트웨어 개발 보안 가이드를 기반으로 프로젝트의 보안성을 강화하기 위한 지침과 실행 결과를 정리합니다.

## 1. 입력 데이터 검증 및 표현
- **XSS(Cross-Site Scripting) 방지 [완료]**:
  - `escapeHTML()` 헬퍼 함수를 모든 관리자 대시보드 및 상세 모달창에 구현하여 `innerHTML` 주입 시 데이터를 이스케이프함.
  - HTML `<meta>` 태그에 CSP(Content Security Policy)를 적용하여 인라인 스크립트 실행을 원천적으로 차단함.
- **SQL 삽입(Injection) 방지 [완료]**:
  - `sanitizeQuery()` 함수를 통해 Supabase(PostgREST) `.or()` 및 `.ilike()` 검색 쿼리에 포함될 수 있는 필터 예약어(괄호, 쉼표, 온점 등)를 사전에 제거하여 필터 인젝션을 차단함.

## 2. 보안 기능
- **인증 및 인가 처리 [보완 완료]**:
  - `sessionStorage` 기반 관리자 체크 로직 외에도 CSP를 통해 비인가 스크립트의 접근을 차단함.
  - DB 레벨의 RLS(Row Level Security) 설정을 통해 API 키 탈취 시에도 데이터 수정 권한을 제한함.
- **중요 정보 암호화 [완료]**:
  - API Key 및 GitHub Token 입력 시 노출을 최소화하고 브라우저 로컬 저장 시 주의 문구를 추가함.

## 3. 시간 및 상태
- **경쟁 조건(Race Condition) 방지 [완료]**:
  - Python 배치 스크립트(`get_stock_data.py`, `get_news_and_analyze.py`, `save_to_db.py`) 실행 시 `.tmp/batch.lock` 파일을 사용하여 중복 실행을 차단함 (1시간 타임아웃 적용).

## 4. 에러 처리
- **정보 노출 방지 [완료]**:
  - Python 스크립트의 `try-except` 블록에서 상세 스택 트레이스(`traceback`) 대신 사용자용 일반 메시지("작업 중 오류가 발생했습니다.")를 기록하도록 수정함.

## 5. 코드 오류
- **자원 해제 부적절 [완료]**:
  - 파이썬 파일 핸들 및 네트워크 세션 사용 시 `try-finally`와 `with` 구문을 사용하여 자원 해제를 보장함 (특히 락 파일 제거 로직).
- **널 포인터 역참조 방지 [완료]**:
  - JavaScript의 선택적 체이닝(`?.`) 및 널 병합 연산자(`??`)를 적극 활용하여 데이터 유실 시 화면 크래시를 방지함.

## 6. 캡슐화
- **데이터 노출 방지 [보완 완료]**:
  - `escapeHTML`을 통해 렌더링 단계에서 데이터 간섭을 차단하고, `sessionStorage` 사용 범위를 최소화함.

## 7. API 오용
- **안전하지 않은 API 사용 [보완 완료]**:
  - CSP 설정을 통해 허용된 도메인(`cdn.jsdelivr.net`, `supabase.co`, `api.github.com`)으로만 네트워크 요청이 발생하도록 제한함.
