# FinPass AI 제품 요구사항

## 1. 제품 개요

FinPass AI는 모바일 앱, 챗봇, 콜센터, 영업점처럼 분리된 금융 채널 사이에서 고객의 업무 맥락을 이어주는 AI 기반 Journey Intelligence 서비스다.

앱 행동 이벤트, 오류 이력, 상담 내용, 금융상품 정보와 고객 특성을 결합해 다음을 해석한다.

- 고객이 현재 수행 중인 금융업무
- 완료한 단계와 실패한 지점
- 반복 오류와 상담 필요 수준
- 다음 담당자가 확인하거나 안내해야 할 내용

FinPass AI는 모든 금융 로그를 하나로 복제하는 통합 CRM이 아니다. 현재 업무에 필요한 최소 정보만 `Context Pass`로 구성해 다음 채널에 전달하는 **Financial Journey Context Layer**다.

## 2. 문제와 목표

### 문제

채널별 시스템과 업무정보가 분리되어 고객은 채널 또는 담당자가 바뀔 때 상품, 진행 단계, 오류, 기존 안내, 제출 서류를 반복 설명해야 한다. 직원도 여러 시스템에서 이전 이력을 다시 확인해야 한다.

### 제품 목표

> 고객의 현재 금융업무 상태와 실패 맥락을 AI가 해석하여 다음 채널이 즉시 업무를 이어받도록 한다.

### 성공 가설

1. AI Context Summary는 원시 로그만 제공할 때보다 상담원의 상황 파악 시간을 단축한다.
2. Failure Detection은 단순 오류와 실제 상담이 필요한 고객을 구분한다.
3. Journey Context와 RAG 기반 추천 조치는 상담원의 매뉴얼 탐색 시간을 줄인다.
4. Context 전달은 고객의 반복 설명과 업무 재시작을 줄인다.
5. Journey Analytics는 개별 로그에서 찾기 어려운 구조적 병목을 드러낸다.

## 3. 핵심 사용자

| 사용자 | 주요 요구 |
| --- | --- |
| 금융소비자 | 채널이 바뀌어도 설명과 입력을 반복하지 않고 업무를 이어서 처리 |
| 콜센터 상담원 | 이전 Journey와 실패 원인을 빠르게 파악하고 적절한 후속 절차 수행 |
| 영업점 직원 | 모바일·콜센터 진행 내역을 확인하고 남은 절차만 수행 |
| 채널/서비스 운영 관리자 | 오류, 이탈, 상담 전환과 채널 이동의 구조적 원인 분석 |

영업점 전용 화면은 MVP 후순위지만 Context Pass는 향후 영업점 채널을 수용할 수 있게 설계한다.

## 4. MVP 범위

### 대상 업무

`개인사업자 대출 신청` 단일 Journey를 구현한다.

정상 흐름:

`상품조회 → 사업자 정보 입력 → 본인인증 → 한도조회 → 소득정보 확인 → 서류제출 → 신청완료`

대표 실패 흐름:

`상품조회 → 본인인증 완료 → 한도조회 완료 → 소득인증 오류 3회 → 상담 연결 → Context 공유 동의 → 상담원의 대체 증빙 안내 → 서류제출부터 재개`

### 반드시 구현

- Customer Journey 웹 Mock과 이벤트 추적
- Journey 상태 관리 및 Failure Detection
- 동의 관리와 Context Pass
- AI Context Interpretation
- Agent Copilot과 Suggested Next Best Action
- 상담 결과의 Reverse Handoff 및 Journey Resume
- Admin Journey Analytics

### 후순위

- Kafka 기반 실시간 스트림
- 고급 Sequence Model
- 영업점 전용 채널
- 음성 STT, 실제 은행 인증과 다기관 연동
- 프로덕션 수준 IAM

## 5. End-to-End 사용자 흐름

1. 고객이 웹 기반 금융 앱에서 개인사업자 대출을 선택한다.
2. 각 화면 행동과 업무 결과가 Journey Event로 저장된다.
3. 소득인증 오류가 반복되면 Failure Detection이 상담 필요 상태를 판정한다.
4. 고객이 상담 연결을 선택하고 Context 공유 범위와 만료 조건에 동의한다.
5. 시스템이 최소 업무정보로 Context Pass를 생성한다.
6. 상담원은 Timeline, AI Summary, Failure Evidence, Intent를 조회한다.
7. 시스템은 매뉴얼, 상품정보와 유사 상담 사례를 검색해 근거가 있는 추천 조치를 제시한다.
8. 상담원이 후속 조치를 선택하고 상담 결과를 등록한다.
9. 고객 채널에 결과와 재개 지점이 전달된다.
10. 고객은 서류제출 단계에서 업무를 재개한다.
11. 관리자 Dashboard에 Journey 상태와 통계가 반영된다.

## 6. 핵심 기능 요구사항

### 6.1 Customer App

- 로그인 또는 데모 고객 선택
- 상품 목록 및 개인사업자 대출 신청
- Journey 진행 상태 표시
- 소득인증 실패와 재시도 시뮬레이션
- 상담 연결 및 Context 공유 동의
- 상담 상태·결과 확인
- 지정된 단계부터 Journey 재개

### 6.2 Context Interpretation

입력은 Journey Event, 오류 이력, 최근 화면 이동, 고객 문의, 이전 상담 요약이다. Rule Engine이 완료 단계, 실패 단계, 오류 횟수처럼 확정 가능한 사실을 계산하고 LLM이 JSON Schema에 맞는 자연어 Context로 변환한다.

필수 출력:

- 현재 상품과 단계
- 완료 단계
- 실패 단계와 오류 코드
- 재시도 횟수
- 고객 Intent
- 상담원용 요약
- 사실 근거가 되는 이벤트 ID

### 6.3 Journey Failure Detection

MVP는 규칙 기반 점수 모델을 사용한다.

주요 Feature:

- `retry_count`, `error_count`, `step_duration`
- `back_navigation_count`, `same_screen_repeat_count`
- `session_duration`, `previous_failure_count`
- `channel_transition_count`

판정 값:

- `NORMAL`
- `RETRY_EXPECTED`
- `ASSISTANCE_RECOMMENDED`
- `CRITICAL_FAILURE`

규칙과 임계값은 코드와 설정으로 버전 관리하고 판정 사유를 함께 저장한다.

### 6.4 Context Pass와 동의

Context Pass는 다음 최소 정보로 제한한다.

- Journey, 상품, 현재 단계와 완료 단계
- 실패 단계, 오류 코드, 재시도 횟수
- 제출 서류 목록
- 고객 Intent와 AI Summary
- 동의 범위, 생성·만료 시각

만료되거나 철회된 동의로는 새 조회를 허용하지 않는다. 원본 이벤트는 Context Pass에 복제하지 않고 참조 ID와 요약 근거만 보관한다.

### 6.5 Agent Copilot

- Customer Journey Timeline
- AI Context Summary
- Failure Evidence와 Intent
- 근거가 포함된 Suggested Next Best Action
- 유사 상담 사례
- 상담 결과, 요청 서류, 재개 단계 등록

AI 추천은 상담원의 판단을 돕는 후보이며 자동으로 고객 업무를 변경하지 않는다.

### 6.6 Suggested Next Best Action

현재 Context로 검색 질의를 생성하고 금융업무 매뉴얼, 금융상품 정보, 유사 상담 사례를 Vector Search한다. LLM은 검색 결과 안에서만 Action Candidate를 생성한다.

각 후보는 다음을 포함한다.

- 조치명과 설명
- 추천 이유
- 근거 문서 또는 사례 ID
- 신뢰도 또는 적용 조건

### 6.7 Admin Analytics

필수 KPI:

- 전체 Journey 수와 완료율
- 실패율과 상담 전환율
- 평균 Journey 소요시간
- 단계별 Funnel과 이탈률
- 상위 실패 단계와 오류 코드
- 채널 전환 패턴
- 고객 특성별 Failure Rate

AI Insight는 집계 쿼리 결과만 설명하며 수치와 집계 기간을 함께 표시한다.

## 7. 데이터 전략

| 데이터셋 | MVP 활용 |
| --- | --- |
| AI-Hub 금융 고객상담 | 상담 Intent·요약 분석, 유사 사례 검색, 국내 금융 상담 문체 |
| AI-Hub 금융상품/소비자 특성 | 상품 Knowledge Base와 주요 확인 항목 구성 |
| BPI Challenge 2017 | 대출 Process 구조, Sequence·반복·이탈 패턴, Synthetic 생성 기반 |
| Banking77 | 금융 Intent Taxonomy 매핑과 분류 실험 |

공개되지 않은 모바일 클릭·오류 로그는 위 데이터의 구조와 패턴을 바탕으로 Synthetic Journey Dataset을 생성해 대체한다.

### 표준 Event Schema

`event_id`, `customer_id`, `journey_id`, `session_id`, `channel`, `event_type`, `product_type`, `journey_step`, `status`, `error_code`, `retry_count`, `timestamp`, `duration`

대표 Event Type은 `JOURNEY_STARTED`, `PRODUCT_VIEWED`, `IDENTITY_VERIFICATION_COMPLETED`, `LIMIT_CHECK_COMPLETED`, `INCOME_VERIFICATION_FAILED`, `SUPPORT_REQUESTED`, `CALL_COMPLETED`, `DOCUMENT_REQUIRED`, `JOURNEY_RESUMED`, `JOURNEY_COMPLETED` 등이다.

## 8. 품질 및 비기능 요구사항

- 모든 쓰기 API는 중복 이벤트를 방지할 수 있어야 한다.
- Journey 상태 변경과 상담 결과는 감사 가능한 이력을 남긴다.
- PII와 업무 Context를 분리하며 로그에 민감정보를 기록하지 않는다.
- LLM 호출 실패 시 규칙 기반 Context와 정적 추천으로 기능을 유지한다.
- AI 출력은 JSON Schema 검증 후 저장·노출한다.
- 추천과 요약에는 사용한 이벤트 및 Knowledge 근거를 연결한다.
- 시간은 저장 시 UTC, 화면 표시 시 사용자 시간대로 처리한다.

## 9. 평가 지표

| 기능 | 지표 |
| --- | --- |
| Context Interpretation | Fact Consistency, Completeness, Hallucination Rate, 요약 품질 |
| Failure Detection | Precision, Recall, F1, False Positive Rate |
| Next Best Action | Top-K Accuracy, Manual Grounding Rate, Retrieval Precision |
| Journey Analytics | 원본 집계와 AI 설명의 수치·기간 일치율 |

PoC에서는 추가로 상담원의 상황 파악 시간, 매뉴얼 탐색 시간, 고객 반복 설명 횟수, Journey 재시작률을 전후 비교한다.

## 10. MVP 완료 기준

대표 실패 시나리오가 Customer App → Backend → Agent Copilot → Customer App → Admin Dashboard 순서로 실제 동작해야 한다. 모든 이벤트가 저장되고, 반복 실패 판정과 동의 기반 Context Pass가 생성되며, 상담원이 근거 기반 추천을 사용해 상담을 완료한 뒤 고객이 서류제출 단계부터 재개할 수 있어야 한다. 해당 결과는 관리자 통계에 즉시 반영되어야 한다.
