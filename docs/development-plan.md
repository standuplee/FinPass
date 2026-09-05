# FinPass AI MVP 개발 계획

## 1. 실행 전략

개발은 기술 계층별 완성이 아니라 대표 실패 시나리오를 관통하는 수직 슬라이스로 진행한다. 먼저 고정 Seed 데이터와 규칙 기반 기능으로 전체 흐름을 연결한 뒤 실제 데이터 처리, LLM, RAG와 Analytics 정밀도를 높인다.

예상 기간은 소규모 팀 기준 10주이며 팀 규모와 데이터 접근 승인에 따라 조정한다.

## 2. 단계별 로드맵

| 단계 | 기간 | 핵심 결과 |
| --- | --- | --- |
| 0. 기반·데이터 계약 | 1주 | 개발환경, Unified Schema, 데이터 프로파일과 라이선스 기록 |
| 1. Journey 수직 슬라이스 | 2주 | Customer 흐름, Event 저장, 상태 관리, 반복 실패 판정 |
| 2. Handoff와 Copilot | 2주 | Consent, Context Pass, 상담 Timeline, 상담 완료·Resume |
| 3. AI Context와 RAG | 2주 | Structured Summary, 검색 인덱스, 근거 기반 추천 조치 |
| 4. Synthetic·평가 | 1주 | 10k+ Journey 생성, Failure/AI 평가 Harness |
| 5. Admin Analytics | 1주 | KPI, Funnel, 오류·채널·Segment 분석과 Insight |
| 6. 통합·PoC 준비 | 1주 | E2E, 보안·Fallback 검증, 데모와 실험 계획 |

## 3. Phase 0 — 기반과 데이터 분석

### 작업

- `apps/web`, `apps/api`, `packages/contracts`, `ai/evals`, `pipelines` 중심의 모노레포 패키지 구성
- Frontend, Backend, PostgreSQL/pgvector 개발환경 구성
- OpenAPI에서 TypeScript API Client와 공용 계약 타입을 생성하는 흐름 구성
- Event, Entity, API의 버전 1 계약 정의
- AI-Hub 두 데이터셋의 필드, 크기, 품질, 라이선스·반출 조건 기록
- BPI 2017 Event와 FinPass 단계 매핑
- Banking77 Intent와 내부 Intent Taxonomy 매핑
- PII 분류, 보관 제외 항목, 가명화 규칙 정의
- Dataset Provenance와 재현 가능한 전처리 스크립트 작성

### 산출물

- 실행 가능한 Web/API 패키지 Skeleton과 의존성 경계
- ERD, OpenAPI 초안, Event Catalog와 생성된 TypeScript Contract
- Dataset Profile과 Mapping Table
- 로컬 실행 환경 및 CI 기본 구성

### 완료 조건

- 대표 정상·실패 Event Fixture가 Unified Schema 검증을 통과한다.
- `JourneyEvent → Journey State` 변환 규칙이 예제로 합의된다.
- 원본 데이터 없이도 Seed 데이터로 개발을 시작할 수 있다.

## 4. Phase 1 — Journey 수직 슬라이스

### 작업

- Journey 생성과 append-only Event 저장
- 중복 방지와 상태 Projection
- Customer App의 상품조회부터 소득인증까지 구현
- 실패 시나리오용 A104 오류와 재시도 이벤트 구현
- Failure Feature와 설명 가능한 Rule Engine 구현
- Timeline 조회 API와 기본 화면 구현

### 완료 조건

- 고객 클릭이 서버 Event로 기록되고 새로고침 후에도 상태가 유지된다.
- 동일 이벤트 재전송 시 중복 저장되지 않는다.
- A104 3회 실패 시 `ASSISTANCE_RECOMMENDED`와 판정 근거가 생성된다.
- 정상 흐름은 잘못된 상담 추천을 발생시키지 않는다.

## 5. Phase 2 — Context Handoff와 Agent Copilot

### 작업

- Consent 생성, 만료, 철회와 Scope 검증
- 최소 필드 기반 Context Pass 생성
- Agent Copilot의 Timeline, Failure Evidence, Intent 영역
- 상담 생성·완료 및 후속 조치 등록
- `resume_step`을 포함하는 Reverse Handoff
- Customer App 상담 결과와 서류제출 재개 화면

### 완료 조건

- 유효한 동의 없이는 Context Pass가 생성·조회되지 않는다.
- 상담원이 원본 전체 로그 없이 필요한 맥락을 확인할 수 있다.
- 상담 완료 후 해당 고객만 지정 단계에서 재개할 수 있다.
- 생성, 조회, 상담 완료가 Audit Log에 남는다.

## 6. Phase 3 — AI Context Interpretation와 RAG

### 작업

- 사실 계산용 Context Fact Builder
- JSON Schema 기반 LLM Gateway와 Prompt 버전 관리
- Template Summary Fallback
- Mock 금융업무 매뉴얼 작성 및 금융상품 데이터 정규화
- 상담 사례 Chunking·Embedding·pgvector 적재
- Hybrid Metadata/Vector 검색과 Evidence Bundle
- 근거가 포함된 최대 3개 Suggested Action 생성

### 완료 조건

- 요약의 모든 주요 사실이 Event ID로 추적된다.
- Schema 오류와 LLM 장애 시에도 Agent 화면이 동작한다.
- 추천 조치마다 매뉴얼 또는 사례 근거가 표시된다.
- 검색 근거가 없을 때 시스템이 조치를 추측하지 않는다.

## 7. Phase 4 — Synthetic 데이터와 모델 평가

### 작업

- 정상, 재시도 성공, 상담 필요, 치명 실패 Journey Template 정의
- BPI 기반 단계 전이와 소요시간 분포 적용
- Intent, 고객 Segment, 오류 코드 분포 결합
- 고정 Random Seed와 Generator 버전 기록
- 10,000 Journey 우선 생성 후 성능에 따라 50,000까지 확장
- 규칙 모델 평가와 임계값 Calibration
- Context/RAG 평가용 Golden Set 구축

### 완료 조건

- 동일 버전과 Seed로 데이터가 재생성된다.
- 클래스 분포와 전이 규칙을 자동 검증한다.
- Failure Detection의 Precision, Recall, F1, FPR 리포트가 생성된다.
- 요약 Fact Consistency와 추천 Grounding을 자동·수동 평가할 수 있다.

## 8. Phase 5 — Admin Analytics

### 작업

- Journey, 실패, 상담 전환 집계 쿼리
- 단계별 Funnel과 체류시간
- Error Code와 고객 Segment별 비교
- 채널 전환 분석
- 기간 필터와 집계 시각 표시
- 집계 JSON만 입력받는 AI Insight 생성

### 완료 조건

- 대표 Journey 완료 직후 KPI에 반영된다.
- Dashboard 수치가 검증용 SQL 결과와 일치한다.
- AI Insight의 모든 수치가 입력 집계에서 확인된다.
- 데이터가 부족한 Segment는 오해를 유발하지 않게 표시된다.

## 9. Phase 6 — 통합, 품질, PoC 준비

### 작업

- 전체 대표 시나리오 Playwright E2E
- API·Domain Unit/Integration Test 보강
- 동의 만료·철회, 중복 Event, LLM Timeout, 빈 검색 결과 테스트
- Seed/Reset Script와 데모 실행 가이드
- PoC 실험 과업, 측정 방식과 설문 설계
- 성능·접근성·보안 기본 점검

### Release Gate

- PRD의 MVP 완료 시나리오가 한 번의 데모 세션에서 끝까지 성공한다.
- 핵심 경로 E2E와 Domain Test가 CI에서 통과한다.
- AI가 없어도 Fallback으로 Journey Handoff가 가능하다.
- Context Pass 동의 및 만료 검증에 우회 경로가 없다.
- Demo 데이터 Reset과 재현 절차가 문서화되어 있다.

## 10. 우선순위 Backlog

### P0 — E2E에 필수

- Event/State 계약과 Journey Engine
- Customer 실패 시나리오
- Failure Rule과 판정 근거
- Consent, Context Pass, Agent Timeline
- 상담 완료와 Resume
- 기본 Analytics

### P1 — AI 가치 검증

- Structured Context Summary와 Fallback
- 금융 매뉴얼·상품 KB
- Similar Cases와 근거 기반 Action
- Synthetic Generator와 평가 Harness
- AI Analytics Insight

### P2 — 견고성·확장

- ML Failure Model Shadow 비교
- 고급 Hybrid Retrieval/Reranking
- 별도 Worker와 비동기 처리
- 역할별 Frontend/서비스 분리
- 영업점, STT, 외부 기관 연동

## 11. 테스트 전략

| 계층 | 주요 검증 |
| --- | --- |
| Domain Unit | 상태 전이, Feature, Failure Rule, Resume 계산 |
| API Integration | DB 저장, 멱등성, 동의·만료, 권한 경계 |
| Data Contract | Dataset Mapping, Event Schema, Synthetic 분포 |
| AI Evaluation | Schema, Fact Consistency, Grounding, Fallback |
| Frontend Component | 단계 표시, 오류·동의·추천 상태 |
| E2E | 고객 실패 → 상담 → 서류제출 재개 → Analytics 반영 |

Golden Journey Fixture를 정상 1개, 실패 후 상담 1개, 동의 만료 1개, 잘못된 상태 전이 1개 이상 유지한다.

## 12. PoC 검증 계획

내부 상담원 역할 참가자에게 동일한 고객 상황을 원시 로그 방식과 FinPass Copilot 방식으로 각각 수행하게 한다.

측정 항목:

- 올바른 상황 파악까지 걸린 시간
- 필요한 매뉴얼·절차 발견 시간
- 핵심 사실 누락과 오판 수
- 고객에게 다시 질문해야 한 항목 수
- 추천 조치 채택률과 유용성 평가

순서 효과를 줄이기 위해 참가자별 시나리오 순서를 교차하고, AI 출력의 정확도와 UX 효과를 별도로 평가한다.

## 13. 주요 리스크와 대응

| 리스크 | 대응 |
| --- | --- |
| AI-Hub 접근·라이선스 지연 | Seed/Mock 문서로 E2E 선행, Provenance 분리 |
| Synthetic 데이터 편향 | BPI 분포 근거 기록, 다양한 Template과 민감도 분석 |
| LLM Hallucination | Fact Builder, JSON Schema, Evidence 검증, Fallback |
| RAG가 유사하지만 잘못된 사례 추천 | 매뉴얼 우선, Metadata Filter, 근거 표시, 자동 실행 금지 |
| 과도한 Context 공유 | 최소 필드 Allowlist, 동의 Scope·만료 검증, Audit |
| Analytics와 AI 설명 불일치 | 집계 결과만 모델에 전달, 수치 사후 검증 |
| MVP 범위 확대 | 개인사업자 대출 단일 시나리오와 P0 Release Gate 고정 |

## 14. 초기 구현 순서

첫 두 Iteration에서는 다음 순서를 권장한다.

1. Event Catalog, ERD, 상태 전이와 API Contract를 확정한다.
2. PostgreSQL 모델과 Journey/Event API를 구현한다.
3. Customer App에서 정상·실패 Event를 실제로 발생시킨다.
4. 규칙 기반 Failure 판정과 Timeline을 연결한다.
5. Consent와 Context Pass를 구현한다.
6. Agent 상담 완료가 Customer Resume로 이어지게 한다.
7. 이 수직 슬라이스가 통과한 뒤 LLM과 RAG를 연결한다.
