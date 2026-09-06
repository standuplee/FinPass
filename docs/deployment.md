# FinPass AI 배포 가이드

## 권장 구성

심사위원용 MVP는 GitHub Pages에 Web을 배포하고, Render의 FastAPI와
Supabase PostgreSQL을 연결하는 구성을 사용한다.

```text
GitHub Pages Web
      ↓ NEXT_PUBLIC_API_URL
Render FastAPI
      ↓ DATABASE_URL
Supabase PostgreSQL + pgvector
```

## Supabase 설정

1. Supabase 프로젝트를 생성한다.
2. SQL Editor에서 `CREATE EXTENSION IF NOT EXISTS vector;`와
   `CREATE EXTENSION IF NOT EXISTS pgcrypto;`를 실행한다.
3. Connect 화면의 pooled 또는 direct PostgreSQL URL을 복사한다.
4. URL의 사용자·비밀번호·호스트를 Render `DATABASE_URL`에 등록한다.

## Render API 설정

`render.yaml`을 Blueprint로 등록한다. 다음 환경변수를 입력한다.

| 변수 | 값 |
| --- | --- |
| `DATABASE_URL` | Supabase PostgreSQL URL |
| `CORS_ORIGINS` | `https://<github-id>.github.io` 및 프로젝트 Pages URL |
| `OPENAI_API_KEY` | 선택 사항. 미설정 시 로컬 fallback 사용 |

배포 후 Render API의 `/health`와 `/ready`가 각각 `200`인지 확인한다.
Migration은 Render Shell에서 다음 명령으로 최초 한 번 실행한다.

```bash
cd /app
uv run alembic upgrade head
```

## GitHub Pages 설정

Repository Settings → Pages에서 Source를 `GitHub Actions`로 선택한다.
Repository Variables에 `PUBLIC_API_URL`을 추가하고 Render API URL을 입력한다.
이후 `main` push마다 정적 Web이 자동 배포된다.

Pages URL은 다음 형식이다.

```text
https://<github-id>.github.io/<repository-name>/customer/
https://<github-id>.github.io/<repository-name>/agent/
https://<github-id>.github.io/<repository-name>/admin/
```

## 심사위원용 검증

고객 앱에서 대출 신청을 시작하고 본인 인증 `AUTH_TIMEOUT`, 한도 조회
`NT004` 오류를 차례로 확인한다. 챗봇에 “왜 인증이 되지 않나요?”라고
질문한 뒤 답변에 현재 단계와 오류 정보가 반영되는지 확인한다. 콜센터 또는
영업점 연결을 선택하고 Context 공유에 동의하면 Agent Copilot에서 Context
Summary, 실패 근거, Next Best Action을 확인할 수 있다.
