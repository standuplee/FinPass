# Journey Event Catalog v1

## 공통 Envelope

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `schema_version` | string | Y | 현재 `1.0` |
| `event_id` | UUID | Y | 전역 고유, 멱등 처리 키 |
| `customer_id` | UUID | Y | 내부 가명 고객 ID |
| `journey_id` | UUID | Y | Journey 내 모든 Event에서 동일 |
| `session_id` | UUID | Y | 채널 세션 식별자 |
| `channel` | enum | Y | Customer App, Chatbot, Call Center, Branch |
| `event_type` | enum | Y | 아래 Catalog 참조 |
| `product_type` | enum | Y | MVP는 `SOLE_PROPRIETOR_LOAN` |
| `journey_step` | enum | Y | 표준 Journey 단계 |
| `status` | enum | Y | Started, Succeeded, Failed, Requested, Completed |
| `error_code` | string | 조건부 | `FAILED`인 경우 필수, 그 외 금지 |
| `retry_count` | integer | Y | 0 이상, 동일 단계의 누적 재시도 |
| `occurred_at` | ISO 8601 | Y | UTC 저장 |
| `duration_ms` | integer | N | 0 이상 |
| `attributes` | object | N | PII 금지, Event별 Allowlist 적용 예정 |

## Event 정의

| Event | Step | 의미 |
| --- | --- | --- |
| `JOURNEY_STARTED` | Product Selection | 대출 Journey 시작 |
| `PRODUCT_VIEWED` | Product Selection | 대상 상품 상세 조회 |
| `BUSINESS_INFORMATION_COMPLETED` | Business Information | 사업자 기본정보 입력 완료 |
| `IDENTITY_VERIFICATION_STARTED/COMPLETED` | Identity Verification | 본인인증 시작/완료 |
| `LIMIT_CHECK_STARTED/COMPLETED` | Limit Check | 한도조회 시작/완료 |
| `INCOME_VERIFICATION_STARTED/COMPLETED/FAILED` | Income Verification | 소득인증 시작/완료/실패 |
| `DOCUMENT_UPLOAD_STARTED/COMPLETED/FAILED` | Document Submission | 서류제출 시작/완료/실패 |
| `SUPPORT_REQUESTED` | Support | 고객의 상담 연결 요청 |
| `CONTEXT_SHARING_CONSENTED` | Support | Context 공유 동의 완료 |
| `CALL_STARTED/COMPLETED` | Support | 상담 시작/종료 |
| `DOCUMENT_REQUIRED` | Document Submission | 상담원이 추가서류 요청 |
| `JOURNEY_RESUMED` | Support | 지정 단계부터 고객 업무 재개 |
| `JOURNEY_COMPLETED` | Application Completion | 신청 완료 |

Python 계약의 기준은 `apps/api/app/contracts/events.py`, 사람이 검토하는 단계 매핑의 기준은 `knowledge/taxonomy/event-types.yaml`이다. 변경 시 둘과 OpenAPI 계약을 함께 갱신한다.
