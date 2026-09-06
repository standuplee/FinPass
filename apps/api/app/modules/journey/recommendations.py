from app.contracts.ai import EvidenceReference, RecommendedActionOutput
from app.modules.journey.interpretation import interpret_journey


def recommend_actions(session, journey_id) -> list[RecommendedActionOutput]:
    context = interpret_journey(session, journey_id)
    evidence = [item for item in context.evidence if item.source_type == "JOURNEY_EVENT"]
    if "A104" in context.error_codes:
        return [
            RecommendedActionOutput(
                action_code="VERIFY_ALTERNATE_INCOME",
                title="사업자 소득유형 확인",
                description=(
                    "사업자 소득금액증명원 또는 부가세 과세표준증명원 "
                    "제출 가능 여부를 확인합니다."
                ),
                rationale="소득인증 A104 오류가 반복되어 대체 소득증빙 검토가 필요합니다.",
                conditions=["고객 본인 확인", "최근 발급 서류 여부 확인"],
                evidence=evidence
                + [
                    EvidenceReference(
                        source_type="MANUAL", source_id="income-verification-a104"
                    )
                ],
            ),
            RecommendedActionOutput(
                action_code="SEND_DOCUMENT_LINK",
                title="모바일 서류 제출 링크 제공",
                description=(
                    "상담 완료 후 고객이 서류 제출 단계에서 재개할 수 있도록 "
                    "제출 링크를 안내합니다."
                ),
                rationale=(
                    "Journey를 처음부터 재시작하지 않고 중단된 단계부터 "
                    "이어가기 위한 조치입니다."
                ),
                evidence=evidence
                + [
                    EvidenceReference(
                        source_type="PRODUCT", source_id="SOLE_PROPRIETOR_LOAN"
                    )
                ],
            ),
        ]
    return [
        RecommendedActionOutput(
            action_code="REVIEW_CURRENT_STEP",
            title="현재 단계 확인",
            description="고객의 현재 단계와 미완료 입력 항목을 확인합니다.",
            rationale="실패 근거가 부족한 경우 확정된 Journey 사실을 먼저 확인해야 합니다.",
            evidence=evidence,
        )
    ]
