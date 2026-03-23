# 메인 홈페이지 개편 분석 및 진행 계획 (index_plan.md)

제공해주신 이미지의 "톤 앤 매너"와 "화면 구도"를 유지하면서, 현재 시스템의 증권 데이터를 효과적으로 보여줄 수 있도록 홈페이지를 개편합니다.

## 1. 프로젝트 분석 및 구도 기획

### 1.1 현재 화면 구도 (제공 이미지 참고)
- **상부 (Main Content)**: 3x3 행렬(Total 9개)의 타일형 뉴스 카드 레이아웃.
- **하부 (Newsletter)**: "Stay Updated with Our Newsletter" 문구와 함께 이메일 입력창 및 구독 버튼 배치.
- **색감**: 깔끔한 화이트 배경, 모던한 타이포그래피, 절제된 보더 및 쉐도우 사용.

### 1.2 뉴스 카드 데이터 구성
각 타일에는 다음 5가지 핵심 정보를 표시합니다:
1. **회사명**: 해당 뉴스의 대상 기업 (예: 삼성전자)
2. **기사 타이틀**: 뉴스의 제목
3. **기사 내용**: 뉴스의 짧은 요약(Snippet)
4. **투자 지표**: 해당 기업의 주요 지표 (PER, PBR, 기대수익률 등)
5. **게시 일자**: 기사가 작성된 시간

## 2. 기술적 구현 계획

### 2.1 데이터 연동 계획 (Supabase)
- **Query**: `news_articles` 테이블에서 최신 9개 기사를 가져오며, `companies` 테이블과 Join하여 해당 기업의 지표(Equity Indicators)를 함께 조회합니다.
- **Fields**: `company_name`, `title`, `snippet`, `published_at`, `companies(per, pbr, expected_return)`.

### 2.2 UI/UX 구현 계획 (CSS/HTML)
- **Grid System**: `display: grid` 및 `grid-template-columns: repeat(3, 1fr)`을 사용하여 3x3 구도를 완벽하게 재현합니다.
- **Responsive Design**: 모바일 환경에서는 9개의 카드가 세로로 1열 배치되도록 미디어 쿼리를 적용합니다.
- **Card Styling**: 
  - `background: #ffffff`, `border: 1px solid #e1e4e8`, `border-radius: 8px`.
  - 회사명은 상단에 작고 구분감 있게 배치 (Capitalized).

## 3. 작업 로드맵

1. `index_plan.md` 작성 및 분석 (현재 단계)
2. `public/index.html` 구조 개편 (3x3 그리드 영역 및 뉴스레터 하단 이동)
3. `public/css/index.css` 디자인 고도화 (이미지 톤 앤 매너 반영)
4. `public/js/index.js` 데이터 페칭 로직 추가 (9개 기사 동적 생성)
5. 화면 검증 및 최종 배포 준비

---
*참고: 사용자 요청에 따라 `index_plane.md` 대신 표준적인 `index_plan.md` 경로(docs/)를 사용하여 시스템적으로 관리합니다.*
