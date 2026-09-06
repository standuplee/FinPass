# 로컬 개발 환경

## PostgreSQL 16

macOS에서는 PostgreSQL 16과 pgvector를 사용한다. 기본 개발 계정과
데이터베이스는 다음과 같다.

| 항목 | 값 |
| --- | --- |
| Role | `finpass` |
| Password | `finpass` |
| Development DB | `finpass` |
| Test DB | `finpass_test` |
| Port | `5432` |

로컬 서비스 상태를 확인하고 API 스키마를 적용한다.

```bash
brew services list
make api-migrate
```

`vector`와 `pgcrypto` 확장은 데이터베이스 관리자가 최초 한 번 활성화해야
한다. Docker Compose 환경에서는 `finpass`가 관리자이므로 migration이 직접
생성한다. Homebrew 환경처럼 애플리케이션 Role이 관리자가 아니면 각 DB에서
먼저 실행한다.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

## API

Python 3.12와 `uv`를 사용한다.

```bash
cd apps/api
uv sync --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Journey API는 다음 수직 슬라이스를 제공한다.

- `POST /api/v1/journeys`: 개인사업자 대출 Journey 생성
- `POST /api/v1/journeys/{id}/events`: append-only Event 기록
- `GET /api/v1/journeys/{id}`: 현재 Projection과 Timeline 조회

Event 기록 요청에는 선택적으로 `Idempotency-Key`를 보낼 수 있다. 같은 키와
같은 요청은 기존 결과를 반환하고, 같은 키에 다른 요청을 보내면 `409`를
반환한다. Event 시간은 timezone이 포함된 ISO 8601 값이어야 한다.

## 검증

테스트는 개발 데이터를 지우지 않도록 이름이 `_test`로 끝나는 DB에서만
실행된다.

```bash
cd apps/api
DATABASE_URL=postgresql+psycopg://finpass:finpass@localhost:5432/finpass_test \
  uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg://finpass:finpass@localhost:5432/finpass_test \
  uv run pytest
uv run ruff check .
```

## Embedding Provider

`OPENAI_API_KEY`가 설정되면 `text-embedding-3-small` 모델로 64차원
embedding을 생성한다. OpenAI Embeddings API가 timeout 또는 오류를
반환하면 deterministic local embedding으로 자동 전환한다.

```bash
export OPENAI_API_KEY="your_api_key_here"
export OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
make rag-index
```

API Key를 저장소에 커밋하지 않는다. 현재 pgvector 컬럼은 64차원으로
고정되어 있으므로 다른 모델을 사용할 때도 `dimensions=64`를 유지한다.

통합 테스트는 Journey 생성과 Timeline 저장, Event/요청 멱등성, 잘못된
식별자와 시간 거부, A104 3회 실패 후 `ASSISTANCE_RECOMMENDED` 판정을 검증한다.

대표 Customer → Agent → Admin 흐름은 개발 DB에서 다음 명령으로 재현한다.

```bash
make demo-e2e
```

명령은 A104 3회 실패, Consent·Context Pass, 상담 완료, 서류 제출 단계
Resume, Analytics 반영 결과를 한 번에 출력한다.
