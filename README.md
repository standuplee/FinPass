# FinPass AI

FinPass AI는 금융 채널 사이에서 고객의 업무 맥락을 이어주는 Financial Journey Intelligence 서비스다. MVP는 개인사업자 대출의 소득인증 반복 실패, 상담 인계, 서류제출 재개 흐름을 구현한다.

## 현재 상태

Phase 0 기반과 데이터 계약을 구성했다. 상세 현황과 실행 방법은 [Phase 0 문서](./docs/phase-0.md)를 참고한다.

## 요구 도구

- Node.js 22+
- pnpm 10+
- Python 3.12+
- uv
- Docker와 Docker Compose

## 시작하기

```bash
cp .env.example .env
docker compose up -d postgres
cd apps/api && uv sync --dev && uv run uvicorn app.main:app --reload
pnpm install && pnpm dev:web
```

API는 `http://localhost:8000`, Web은 `http://localhost:3000`에서 실행된다.

## 문서

- [제품 요구사항](./docs/prd.md)
- [MVP 아키텍처](./docs/architecture.md)
- [개발 계획](./docs/development-plan.md)
- [문서 인덱스](./docs/README.md)
