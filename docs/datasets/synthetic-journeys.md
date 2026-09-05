# Synthetic FinPass Journey Dataset v1

## 목적

공개되지 않은 모바일 은행 행동 로그를 대체해 Journey Engine, Failure Detection, Context Pass와 채널 Handoff를 개발·평가한다. 실제 고객 행동률을 주장하는 데이터가 아니라 MVP 시나리오 검증용 합성 데이터다.

## 입력 근거

- BPI 2017 Case Feature: Process 복잡도, 재작업 여부와 Outcome 표본
- AI-Hub 소비자 데이터: 개인 행을 제거한 Segment 주변분포
- FinPass 업무 규칙: 개인사업자 대출 단계와 A104 실패 시나리오
- Dataset Quality Gate: 모든 정규화 입력이 63개 검사를 통과해야 생성 가능

## 구성

| 시나리오 | Journey | 의미 |
| --- | ---: | --- |
| `NORMAL` | 6,500 | 오류 없이 신청 완료 |
| `RETRY_EXPECTED` | 1,500 | A104 1회 후 재시도 성공 |
| `ASSISTANCE_RECOMMENDED` | 1,500 | A104 3회 후 상담 및 서류제출 재개 |
| `CRITICAL_FAILURE` | 500 | SYS500 발생 후 상담 및 서류제출 재개 |

총 10,000 Journey, 136,500 Event와 10,000개 Failure Feature Snapshot을 생성한다.

## 출력

```text
data/synthetic/generated/v1/
├── journeys.jsonl
├── events.jsonl
├── failure_features.jsonl
├── quality-report.json
└── validation-report.json
```

`failure_features`는 전체 Journey 종료 결과가 아니라 Failure Detection을 수행해야 하는 `as_of_event_id` 시점의 정보만 포함한다. 이후 발생하는 상담 연결이나 Resume Event를 Feature에 포함하지 않아 미래 정보 누수를 막는다.

## 재현성

- 계약: `data/contracts/synthetic-journey-v1.json`
- Seed: `20260905`
- Generator Version: `1.0`
- ID: Dataset 내 순번과 Namespace 기반 UUID v5
- 시간 범위: 2026-08-08부터 2026-09-05 UTC

```bash
make validate-data
make generate-synthetic
make validate-synthetic
```

## 검증 결과

- Journey ID 10,000개 및 Event ID 136,500개 모두 고유
- 누락된 Journey 참조와 Case 내부 시간 역행 0건
- 실패 Event의 오류 코드 누락과 정상 Event의 오류 코드 혼입 0건
- Feature–Journey–`as_of_event_id` 연결 오류 0건
- 상담 Journey 2,000건 모두 Context 동의, 상담과 Resume Event 포함
- 계약의 시나리오 분포 및 출력 SHA-256 일치

## 한계

- Segment는 재식별 방지를 위해 집계 주변분포에서 독립적으로 추출하므로 실제 변수 간 상관관계를 보존하지 않는다.
- BPI Case는 Process 복잡도 표본이며 FinPass 모바일 Event의 직접 Label이 아니다.
- 시나리오 비율은 실제 은행의 오류율이 아니라 MVP 평가를 위한 설정값이다.
- 합성 데이터 성능은 실제 고객 대상 모델 성능으로 해석할 수 없다.
