from app.contracts.events import JourneyStep


def classify_intent(step: JourneyStep, error_codes: list[str]) -> tuple[str, float]:
    """Map Journey facts to the controlled Banking77/FinPass intent taxonomy."""
    if "A104" in error_codes or step == JourneyStep.INCOME_VERIFICATION:
        return "SOURCE_OF_FUNDS_VERIFICATION", 0.96
    if step == JourneyStep.IDENTITY_VERIFICATION:
        return "IDENTITY_VERIFICATION_FAILURE", 0.9 if error_codes else 0.72
    if step == JourneyStep.LIMIT_CHECK:
        return "LOAN_LIMIT_CHECK", 0.84
    return "SOLE_PROPRIETOR_LOAN_APPLICATION", 0.78
