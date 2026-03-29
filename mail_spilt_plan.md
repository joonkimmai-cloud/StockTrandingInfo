# 이메일 템플릿(HTML/CSS) 분리 계획서 (mail_spilt_plan.md)

## 1. 개요
현재 `execution/send_email_report.py` 파일 내부에 하드코딩되어 있는 이메일 HTML 구조와 CSS 스타일을 별도의 파일로 분리하여, **가독성 향상, 유지보수 용이성 확보, 그리고 퍼블리싱(디자인) 작업의 독립성**을 보장합니다.

## 2. 목적
* **디자인 및 구조 확인 용이성:** 브라우저에서 `html` 파일만 열어도 메일 폼의 대략적인 디자인을 확인할 수 있도록 합니다.
* **관심사 분리(Separation of Concerns):** 파이썬 백엔드 코드 코어(로직 처리)와 프론트엔드 코드(HTML/CSS)를 물리적으로 분리합니다.

## 3. 구조 변경 계획 (설계)

### 3.1 디렉토리 및 파일 구성
신규 디렉토리를 생성하여 이메일 템플릿 리소스를 관리합니다.

* `templates/` (신규 생성)
  * `templates/email/` (신규 생성)
    * `email_template.html` (신규 생성: 이메일 HTML 구조 문서)
    * `email_style.css` (신규 생성: 이메일 템플릿용 CSS)

### 3.2 파일별 역할
* **`email_template.html`**
  * `<style>` 태그 내용을 비워두거나 특정 치환자(예: `{{ css_content }}`)를 넣어둡니다.
  * 파이썬의 f-string 방식 대신, `str.replace` 또는 템플릿 포맷팅 방식을 안전하게 사용하기 위해 `{{ market_summary }}`, `{{ kr_html }}`, `{{ us_html }}`, `{{ prediction }}`, `{{ time_now }}`와 같은 명시적인 치환자(Placeholder)를 사용합니다.
* **`email_style.css`**
  * 기존 파이썬 코드 내의 `<style> ... </style>` 안에 들어가 있던 순수 CSS 코드를 그대로 옮깁니다.
* **`execution/send_email_report.py` (수정 대상)**
  * `email_template.html`과 `email_style.css` 파일을 읽어옵니다.
  * 읽어온 CSS 내용을 HTML 템플릿의 특정 영역에 주입(Inject)합니다 (메일 클라이언트는 인라인 또는 내부 스타일시트를 요구하기 때문).
  * 파이썬 스크립트에서 구성한 주식 종목 동적 HTML(KR/US 분석 결과 등)을 최종 치환(`replace`)하여 이메일 콘텐츠를 완성합니다.

## 4. 진행 순서 (구현 및 검증)
1. **[구현]** `templates/email` 폴더 생성 및 `email_style.css`, `email_template.html` 파일 작성.
2. **[구현]** `send_email_report.py`의 `build_html_template` 함수 로직을 수정하여, 하드코딩된 HTML 대신 외부 파일을 읽어와서 리턴하도록 변경.
3. **[검증]** 테스트용 스크립트 또는 브라우저 렌더링을 통해 분리된 HTML/CSS가 기존과 동일하게 표출되는지 검증.
4. **[검증]** 실제 이메일 발송 테스트 (나 자신에게 발송) 진행.

---
위 계획에 대해 검토해 주시고, 승인해 주시면 [구현] 단계를 진행하겠습니다.
