# Phase 0 — Foundation & Data Contract

## 범위

Phase 0는 제품 기능을 확장하기 전에 Web/API 실행 기반, 데이터 계약, 상태 전이 예제, 데이터셋 조사 계획을 고정한다. 실제 원본 AI-Hub/BPI 데이터는 아직 저장소에 포함하지 않는다.

## 산출물 현황

| 산출물 | 위치 | 상태 |
| --- | --- | --- |
| Next.js 역할별 화면 Skeleton | `apps/web` | 완료 |
| FastAPI와 Health/Contract API | `apps/api` | 완료 |
| PostgreSQL + pgvector 환경 | `compose.yaml`, `infra/postgres` | 완료 |
| Unified Event/AI Schema | `apps/api/app/contracts` | 완료 |
| 정상·실패 Golden Fixture | `data/synthetic/fixtures` | 완료 |
| 상태 Projection 예제 | `apps/api/app/modules/journey/state.py` | 완료 |
| ERD | `docs/data-model.md` | 완료 |
| Event Catalog | `docs/event-catalog.md` | 완료 |
| OpenAPI 초안 | `docs/api/openapi.yaml` | 완료 |
| Dataset Mapping/Provenance 계획 | `docs/dataset-mapping.md` | 완료 |
| Banking77 고정 리비전 Loader | `pipelines/inspect/banking77.py` | 완료 |
| 상담 정규화·구조화 PII 마스킹 | `pipelines/normalize/consultations.py` | 완료 |
| 상품 중복 제거·소비자 Segment 집계 | `pipelines/normalize/financial_products.py` | 완료 |
| 실제 데이터 Profile | `docs/datasets/profile-2026-09-05.md` | 완료 |

현재 실행 환경에는 Node.js, pnpm, uv, Docker 및 Python 3.12가 설치되어 있지 않아 런타임 테스트와 Lockfile 생성은 보류 상태다. JSON/YAML 문법과 저장소 정적 구조는 검증했다. 요구 도구가 준비되면 아래 명령으로 Release Gate를 확인한다.

## 로컬 실행

필요 도구는 Node.js 22+, pnpm 10+, Python 3.12+, uv, Docker다.

```bash
cp .env.example .env
docker compose up -d postgres
cd apps/api && uv sync --dev && uv run uvicorn app.main:app --reload
pnpm install && pnpm dev:web
```

검증:

```bash
make api-test
make api-lint
make validate-fixtures
make web-check
```

## Phase 1 진입 조건

- Fixture 계약과 상태 Projection 테스트 통과
- API `/health`와 `/api/v1/contracts/event-catalog` 응답 확인
- Web의 세 역할 Route 빌드 성공
- PostgreSQL에서 `vector`, `pgcrypto` Extension 확인
- 실제 사용 데이터의 접근 경로와 라이선스 검토 담당자 지정

마지막 항목은 외부 데이터 취득과 조직 내 이용조건 확인이 필요한 작업이므로 담당자 확인 전에는 Seed/Mock 데이터만 사용한다.
