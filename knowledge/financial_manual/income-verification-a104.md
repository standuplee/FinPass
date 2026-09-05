---
document_id: MANUAL-INCOME-A104
version: "1.0"
product_type: SOLE_PROPRIETOR_LOAN
journey_step: INCOME_VERIFICATION
error_codes: [A104]
---

# 소득인증 A104 대응 절차

이 문서는 FinPass AI MVP 검증용 Mock 업무 매뉴얼이며 실제 금융기관의 업무지침이 아니다.

1. 사업자의 소득유형과 신고기간을 확인한다.
2. 자동 인증을 다시 시도하기 전에 동일 오류 횟수를 확인한다.
3. 반복 실패한 경우 소득금액증명원 또는 부가가치세 과세표준증명 등 대체 증빙 가능 여부를 안내한다.
4. 상담 결과에 요청 서류와 고객이 재개할 `DOCUMENT_SUBMISSION` 단계를 기록한다.
