# FinPass Unified Data Model v1

## ERD

```mermaid
erDiagram
    CUSTOMER ||--o{ JOURNEY : starts
    FINANCIAL_PRODUCT ||--o{ JOURNEY : applies_to
    JOURNEY ||--o{ JOURNEY_EVENT : contains
    JOURNEY ||--o{ CONSENT : authorizes
    JOURNEY ||--o{ CONTEXT_PASS : produces
    CONSENT ||--o{ CONTEXT_PASS : governs
    JOURNEY ||--o{ INTENT : classified_as
    JOURNEY ||--o{ CONSULTATION : receives
    CONTEXT_PASS ||--o{ CONSULTATION : handed_to
    CONSULTATION ||--o{ RECOMMENDED_ACTION : suggests

    CUSTOMER {
        uuid id PK
        string segment
        timestamptz created_at
    }
    FINANCIAL_PRODUCT {
        uuid id PK
        string product_code UK
        string name
        string version
        jsonb requirements
    }
    JOURNEY {
        uuid id PK
        uuid customer_id FK
        uuid product_id FK
        string status
        string current_step
        timestamptz started_at
        timestamptz updated_at
    }
    JOURNEY_EVENT {
        uuid id PK
        uuid journey_id FK
        uuid session_id
        string channel
        string event_type
        string journey_step
        string status
        string error_code
        int retry_count
        timestamptz occurred_at
        int duration_ms
        jsonb attributes
    }
    CONSENT {
        uuid id PK
        uuid journey_id FK
        string purpose
        jsonb scope
        string status
        timestamptz expires_at
    }
    CONTEXT_PASS {
        uuid id PK
        uuid journey_id FK
        uuid consent_id FK
        string schema_version
        jsonb context
        timestamptz expires_at
    }
    INTENT {
        uuid id PK
        uuid journey_id FK
        string taxonomy_code
        float confidence
        string source
    }
    CONSULTATION {
        uuid id PK
        uuid journey_id FK
        uuid context_pass_id FK
        string status
        string resume_step
        jsonb result
    }
    RECOMMENDED_ACTION {
        uuid id PK
        uuid consultation_id FK
        string action_code
        string rationale
        jsonb evidence
    }
```

## Event 원장과 Projection

`JourneyEvent`는 수정하지 않는 원장이다. `Journey.status`와 `Journey.current_step`은 Event를 반영한 조회용 Projection이며, 상태가 불일치하면 Event 원장에서 재생성할 수 있어야 한다.

이벤트 중복 방지 키는 `event_id`다. Phase 1의 Event API는 추가로 `Idempotency-Key`를 받아 동일 요청의 결과를 재사용한다.

## 시간 및 민감정보

- 모든 시각은 UTC `timestamptz`로 저장한다.
- 고객 식별정보는 `Customer`의 별도 보호 영역에 두며 Event `attributes`에 넣지 않는다.
- 허용되지 않은 임의 필드는 API 계약에서 거부한다.
- LLM에는 UUID 대신 요청 단위 가명 식별자를 사용한다.
