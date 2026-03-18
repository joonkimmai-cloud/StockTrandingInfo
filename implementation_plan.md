# 구현 계획서: 자동 증권 정보 수집 및 분석 리포트 시스템

시장 데이터를 수집하고 AI 기반 분석을 실행하며, 구독자에게 이메일로 리포트를 발송하는 자동화 파이프라인을 구축합니다.

## [전문가/개발자 검토 의견]
### 📈 증권 전문가(에널리스트) 관점
> [!TIP]
> - **단순 거래량 vs 상대적 거래량**: 절대적 거래량이 많은 종목(삼성전자 등)은 정보 가치가 낮을 수 있습니다. 전일 대비 **거래량 급증(Relative Volume 200% 이상)** 종목을 우선순위에 두어 시장의 새로운 관심을 포착해야 합니다.
> - **종목 필터링**: 시가 총액 너무 낮은 잡주(Penny Stocks)는 제외하고, 기관 및 외인 수급이 동반된 종목인지 분석에 포함해야 합니다.
> - **매크로 연계**: 개별 종목 뉴스뿐만 아니라 환율, 금리(Fed 의사록 등) 등 매크로 지표와의 연관성을 분석에 반영해야 신뢰도가 높습니다.

### 💻 시니어 개발자 관점
> [!WARNING]
> - **API Rate Limit**: Yahoo Finance와 Naver Finance는 빈번한 요청 시 차단될 수 있습니다. `Retry` 로직과 `Random Delay`를 필수적으로 구현해야 합니다.
> - **비동기 처리**: 20개 종목의 뉴스를 순차적으로 가져오면 시간이 오래 걸립니다. `asyncio` 또는 `threading`을 사용하여 뉴스를 병렬로 수집해야 합니다.
> - **보안**: `.env` 파일 관리를 철저히 하고, 웹 사이트의 이메일 수집 폼에는 `Rate Limiting` 및 `Validation`을 적용하여 스팸 등록을 방지해야 합니다.


## 제안된 변경 사항

### Layer 1: Directives (직무 기술서/SOP)
`directives/` 폴더에 각 단계별 "수행 방법"을 설명하는 마크다운 파일을 생성합니다.

#### [NEW] [stock_collection.md](file:///c:/study/StockTradingTop10/directives/stock_collection.md)
#### [NEW] [ai_analysis.md](file:///c:/study/StockTradingTop10/directives/ai_analysis.md)
#### [NEW] [email_dispatch.md](file:///c:/study/StockTradingTop10/directives/email_dispatch.md)

---

### Layer 3: Execution (실행 스크립트)
`execution/` 폴더에 구체적인 동작을 수행하는 Python 스크립트를 생성합니다.

#### [NEW] [get_stock_data.py](file:///c:/study/StockTradingTop10/execution/get_stock_data.py)
한국(KR) 및 미국(US) 시장에서 **전일 대비 거래량 급증(Relative Volume)** 상위 10개 종목을 추출합니다. 시가총액 필터링을 통해 분석 가치가 있는 종목 위주로 선별합니다.

#### [NEW] [get_news_and_analyze.py](file:///c:/study/StockTradingTop10/execution/get_news_and_analyze.py)
비동기(`asyncio`) 스크래핑을 통해 각 종목의 주요 뉴스와 시장 테마를 수집합니다. Gemini API를 통해 전문 에널리스트 톤으로 경제적 근거(매크로 포함) 중심의 예측 보고서를 생성합니다.

#### [NEW] [send_email_report.py](file:///c:/study/StockTradingTop10/execution/send_email_report.py)
반응형 HTML/Inline CSS를 적용하여 모든 메일 클라이언트에서 가독성이 높은 디자인을 제공합니다. 발송 실패 시 로깅 및 재시도 로직을 포함합니다.


---

### Layer 2: Orchestration (오케스트레이션)
#### [NEW] [main.py](file:///c:/study/StockTradingTop10/main.py)
각 실행 스크립트를 올바른 순서대로 조정하는 전체 프로세스의 진입점(Entry Point)입니다.

---

### 웹 프론트엔드 (구독 등록)
#### [NEW] [Simple UI](file:///c:/study/StockTradingTop10/index.html)
사용자가 이메일을 등록할 수 있는 심플하고 고급스러운 디자인의 랜딩 페이지(Vite 또는 정적 HTML/CSS)입니다.

---

### 데이터베이스 스키마
#### [MODIFY] [supabase_schema.sql](file:///c:/study/StockTradingTop10/supabase_schema.sql)
이메일 관리를 위한 `subscribers` 테이블을 포함하도록 스키마를 업데이트합니다.

## 검증 계획

### 자동화 테스트
- `python execution/get_stock_data.py` 실행 후 `market_data.json`에 20개 종목이 있는지 확인.
- `python execution/get_news_and_analyze.py` 실행 후 `report.json`에 AI 분석 내용과 예측이 포함되었는지 확인.
- `python execution/send_email_report.py` 실행 후 `joonkimm.ai@gmail.com`으로 리포트가 수신되는지 확인.

### 수동 검증
- 웹 인터페이스에 접속하여 이메일을 등록하고, Supabase DB에 정상적으로 추가되는지 확인.
- `main.py`를 수동으로 실행하여 모든 구독자가 이메일을 받는지 확인.
- GitHub Actions를 설정하여 매일 오전 6시(KST)에 배치 작업이 실행되는지 확인.
