# AI 평가 Harness

`make evaluate-ai`는 `data/synthetic/fixtures`의 Golden Journey를 읽어
상태 Projection, 실패 횟수, Intent 분류, Context grounding과 embedding
fallback을 검증한다.

실행 결과는 로컬 산출물인
`data/processed/evaluations/ai-report.json`에 저장된다. 원본 금융 데이터와
평가 리포트는 `.gitignore` 정책에 따라 저장소에 커밋하지 않는다.

현재 MVP 지표:

| 지표 | 의미 |
| --- | --- |
| `state_correct` | 기대 상태와 현재 단계 일치율 |
| `failure_count_correct` | 실패 이벤트 수 일치율 |
| `intent_correct` | Golden Intent 분류 일치율 |
| `context_grounded` | Context가 하나 이상의 Event에서 생성되는지 |
| `fallback_success` | 64차원 fallback embedding의 유효성 |

```bash
make evaluate-ai
```

후속 단계에서는 실제 상담 Golden Set과 pgvector 검색 결과를 추가해
`Recall@K`, `Retrieval Precision`, `Grounding Rate`를 평가한다.
