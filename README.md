# FinPass AI

FinPass AI는 금융 채널 사이에서 고객의 업무 맥락을 이어주는 Financial Journey Intelligence 서비스다. MVP는 개인사업자 대출의 소득인증 반복 실패, 상담 인계, 서류제출 재개 흐름을 구현한다.

## 현재 상태

Phase 0 기반과 데이터 계약을 구성했다. 상세 현황과 실행 방법은 [Phase 0 문서](./docs/phase-0.md)를 참고한다.

## 공개 MVP

Vercel에 배포된 웹 MVP에서 역할별 화면을 바로 확인할 수 있다.

- [FinPass 웹 홈](https://fin-pass-web-ralee.vercel.app)
- [고객 앱](https://fin-pass-web-ralee.vercel.app/customer)
- [상담원 Copilot](https://fin-pass-web-ralee.vercel.app/agent)
- [관리자 Analytics](https://fin-pass-web-ralee.vercel.app/admin)

심사위원용 공개 접속이 필요하면 Vercel 프로젝트의 `Deployment Protection`에서
`Vercel Authentication`을 끈다. 현재 API URL이 별도로 설정되지 않은 환경에서는
화면 Mock 데이터와 프론트엔드 흐름을 우선 검증할 수 있다.

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
