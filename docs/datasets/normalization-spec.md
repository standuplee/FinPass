# Dataset Normalization Specification v1

## 출력 영역

```text
data/processed/
├── consultations/
│   ├── consultations.parquet
│   └── consultation_qa.parquet
├── financial-products/
│   ├── products.parquet
│   └── recommendation_cases.parquet
├── consumers/
│   └── segment_aggregates.parquet
├── process-events/
│   ├── events.jsonl
│   ├── case_features.jsonl
│   └── transition_counts.jsonl
├── intents/
│   └── banking77/{train,test}.parquet
└── rag-documents/
    └── consulting_cases.jsonl
```

## 공통 Provenance 필드

모든 정규화 테이블은 다음 필드를 가진다.

- `dataset_id`, `dataset_version`, `source_split`
- `source_archive`, `source_file`, `source_record_id`
- `source_sha256`
- `normalizer_version`, `normalized_at`

## 상담 정규화

`consultations`에는 상담 Metadata와 비식별 처리 상태를, `consultation_qa`에는 QA 단위를 저장한다. 원문 상담과 고객 속성을 같은 RAG Text로 결합하지 않는다.

RAG 허용 조건:

- 직접 식별자와 연락처 패턴 제거 완료
- 원본 ID를 내부 UUID로 치환
- `pii_scan_status=PASSED`
- 검색 문서에 금융 영역, 상담 주제, Dataset Split만 Metadata로 포함

## 상품 정규화

증권·보험의 서로 다른 필드는 `attributes` JSON에 보존하되 공통 컬럼은 `product_name`, `product_category`, `provider`, `risk_grade`, `source_effective_date`로 승격한다. 필드 오탈자는 Canonical 이름으로 매핑하고 `source_field`를 Provenance에 남긴다.

중복 제거 키는 정렬·정규화한 JSON의 SHA-256이다. 동일한 Train/Validation 원천은 한 번만 적재하고 `observed_splits` 배열에 양쪽 출현을 기록한다.

## 소비자 데이터

개별 행을 제품 Runtime이나 Vector DB에 적재하지 않는다. 연령대, 소득구간, 직업군 등 승인된 Dimension으로 최소 집계한 후 Synthetic 데이터의 분포 설정과 관리자 분석 검증에만 사용한다. 희소 조합은 재식별 위험을 낮추기 위해 최소 집계 기준을 적용한다.

## BPI Process Event

원본 Event는 다음 중간 Schema로 먼저 변환한다.

| 출력 필드 | 원본 |
| --- | --- |
| `case_id` | `case:concept:name` |
| `activity` | `concept:name` |
| `action` | `Action` |
| `origin` | `EventOrigin` |
| `lifecycle` | `lifecycle:transition` |
| `occurred_at` | `time:timestamp` |
| `requested_amount` | `case:RequestedAmount` |
| `accepted`, `selected` | 동명 원본 필드 |

그 후 Synthetic Generator가 Process 패턴을 FinPass `JourneyEvent`로 생성한다. 원본 Case ID를 FinPass 고객 ID로 사용하지 않는다.

초기 정규화 출력은 추가 Runtime 없이 검증 가능한 JSONL을 사용한다. 학습 및 대규모 집계 단계에서 동일 계약을 Parquet으로 변환한다.

재작업 Feature는 동일 Activity 이름의 단순 반복으로 계산하지 않는다. 정상 Workflow lifecycle인 `schedule → start → complete`를 재작업으로 오인하지 않도록 동일 Activity의 `complete`가 두 번 이상 발생하고, 해당 Activity가 검증·미완료·서류보완 관련 Allowlist에 포함될 때만 `has_rework`로 표시한다. 여러 Offer 생성은 별도 상품 제안일 수 있어 재작업 판정에서 제외한다.

## Banking77

제공 Split을 유지하며 `label_text`를 기준으로 내부 Intent 매핑을 별도 테이블에 결합한다. 미매핑은 `UNMAPPED`로 유지하고 억지로 대출 Intent에 포함하지 않는다.
