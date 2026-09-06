# FinPass AI 문서

FinPass AI는 금융소비자가 앱, 챗봇, 콜센터, 영업점 사이를 이동할 때 금융업무의 맥락이 끊기지 않도록 지원하는 **Financial Journey Intelligence Layer**다.

## 문서 구성

| 문서 | 목적 |
| --- | --- |
| [제품 요구사항](./prd.md) | 문제, 사용자, MVP 범위, 핵심 기능과 완료 기준 정의 |
| [MVP 아키텍처](./architecture.md) | 시스템 구성, 데이터 모델, 주요 흐름과 기술 의사결정 정의 |
| [개발 계획](./development-plan.md) | 단계별 산출물, 검증 기준, 우선순위와 리스크 관리 |
| [Phase 0 실행 문서](./phase-0.md) | 개발환경, 계약 산출물, 실행·검증 방법 |
| [로컬 개발 환경](./local-development.md) | PostgreSQL, migration, API 실행·검증 방법 |
| [AI 평가 Harness](./ai-evaluation.md) | Golden Journey 기반 AI·RAG 품질 평가 방법 |
| [Unified Data Model](./data-model.md) | 핵심 Entity, ERD, Event 원장 원칙 |
| [Event Catalog](./event-catalog.md) | Event Envelope와 표준 Event 정의 |
| [Dataset Mapping](./dataset-mapping.md) | 외부 데이터 검사·정규화·Provenance 계획 |
| [Dataset Profile](./datasets/profile-2026-09-05.md) | 확보한 원본의 실제 Schema, 규모와 품질 이슈 |
| [Normalization Spec](./datasets/normalization-spec.md) | 데이터셋별 정규화 출력과 개인정보 처리 원칙 |
| [Dataset Quality Gates](./datasets/quality-gates.md) | 정규화 데이터의 통합 승인 기준과 실행 방법 |
| [Synthetic Journey v1](./datasets/synthetic-journeys.md) | 합성 Journey 구성, 재현성, 검증 결과와 한계 |
| [OpenAPI 초안](./api/openapi.yaml) | Phase 0 HTTP 계약 초안 |

## MVP 핵심 시나리오

개인사업자 대출 신청 중 소득인증에 반복 실패한 고객이 상담 연결을 선택하면, 동의 범위 내에서 Context Pass가 생성된다. 상담원은 이전 Journey, 실패 근거, AI 요약과 추천 조치를 확인하고 대체 소득증빙을 안내한다. 상담 종료 후 고객은 서류제출 단계부터 업무를 재개하며, 결과는 관리자 통계에 반영된다.

## 문서 원칙

- MVP 업무 범위는 개인사업자 대출 신청으로 제한한다.
- 확정적 사실은 규칙과 데이터 조회로 계산하고, LLM은 해석과 표현에 사용한다.
- 채널 간에는 전체 로그가 아닌 동의받은 최소 Context만 전달한다.
- AI 추천은 근거와 함께 제공하며 자동 실행하지 않는다.
- 모든 AI 결과는 구조화하고 추적 가능하게 저장한다.
