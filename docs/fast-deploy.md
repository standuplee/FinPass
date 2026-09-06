# 가장 빠른 공개 배포

심사위원용 URL은 Vercel Web + Render API + Supabase DB 조합으로 만든다.
저장소에 코드와 배포 설정은 준비되어 있으므로 계정 연결과 환경변수 입력만
하면 된다.

## 1. API 먼저 배포

Render에서 New → Blueprint를 선택하고 GitHub의 FinPass 저장소와
`render.yaml`을 연결한다.

필수 환경변수:

```text
DATABASE_URL=<Supabase PostgreSQL URL>
CORS_ORIGINS=https://<Vercel 프로젝트>.vercel.app
APP_ENV=production
```

배포가 끝나면 다음 주소가 `200`인지 확인한다.

```text
https://<render-service>.onrender.com/health
https://<render-service>.onrender.com/ready
```

## 2. Web 배포

Vercel에서 Add New → Project → GitHub Repository를 선택한다.

| 설정 | 값 |
| --- | --- |
| Root Directory | `apps/web` |
| Framework | Next.js |
| Install Command | `pnpm install --frozen-lockfile` |
| Build Command | `pnpm build` |
| Environment Variable | `NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com` |

Deploy 후 Vercel이 발급한 Production URL을 확인한다.

```text
https://<project>.vercel.app/customer
https://<project>.vercel.app/agent
https://<project>.vercel.app/admin
```

## 3. CORS 최종 반영

Render의 `CORS_ORIGINS`를 실제 Vercel URL로 수정하고 API 서비스를 한 번
재배포한다. 브라우저에서 Customer 페이지를 새로고침해 API 호출이 성공하는지
확인한다.

## 4. 심사위원용 5분 테스트

```text
Customer 접속
→ 대출 신청 시작
→ 본인 인증 오류 AUTH_TIMEOUT 확인
→ 재시도 후 한도 조회 이동
→ 한도 조회 오류 NT004 확인
→ 챗봇에서 “왜 인증이 되지 않나요?” 질문
→ Journey Context 기반 답변 확인
→ 콜센터 또는 영업점 선택
→ Context 동의
→ Agent에서 Context Pass 조회
→ AI Summary와 Next Best Action 확인
```

실제 고객 개인정보와 실제 금융 인증을 사용하지 않는 데모 환경임을 제출
문서에 명시한다.
