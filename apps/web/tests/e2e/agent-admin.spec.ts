import { expect, test } from "@playwright/test";

test("agent copilot loads context and recommended actions", async ({ page }) => {
  const journeyId = "31000000-0000-4000-8000-000000000001";
  const passId = "51000000-0000-4000-8000-000000000001";
  await page.route(`**/api/v1/journeys/context-pass/${passId}`, (route) =>
    route.fulfill({ json: { id: passId, journey_id: journeyId, consent_id: "c", payload: { current_step: "INCOME_VERIFICATION", completed_steps: [], failure_step: "INCOME_VERIFICATION", error_codes: ["A104"], retry_count: 3, customer_intent: "SOURCE_OF_FUNDS_VERIFICATION" }, created_at: new Date().toISOString(), expires_at: new Date(Date.now() + 1800000).toISOString() } }),
  );
  await page.route(`**/api/v1/journeys/${journeyId}`, (route) => route.fulfill({ json: { id: journeyId, customer_id: "c", product_type: "SOLE_PROPRIETOR_LOAN", status: "ASSISTANCE_RECOMMENDED", current_step: "INCOME_VERIFICATION", started_at: new Date().toISOString(), updated_at: new Date().toISOString(), events: [{ event_id: "e", customer_id: "c", journey_id: journeyId, session_id: "s", channel: "CUSTOMER_APP", event_type: "INCOME_VERIFICATION_FAILED", product_type: "SOLE_PROPRIETOR_LOAN", journey_step: "INCOME_VERIFICATION", status: "FAILED", error_code: "A104", retry_count: 3, occurred_at: new Date().toISOString(), attributes: {} }] } }));
  await page.route(`**/api/v1/journeys/${journeyId}/analyze`, (route) => route.fulfill({ json: { journey_id: journeyId, current_step: "INCOME_VERIFICATION", completed_steps: [], failure_step: "INCOME_VERIFICATION", error_codes: ["A104"], retry_count: 3, customer_intent: "SOURCE_OF_FUNDS_VERIFICATION", intent_confidence: 0.96, intent_source: "RULE", summary: "소득인증 단계에서 A104 오류가 발생했습니다.", evidence: [{ source_type: "JOURNEY_EVENT", source_id: "e" }] } }));
  await page.route(`**/api/v1/journeys/${journeyId}/actions`, (route) => route.fulfill({ json: [{ action_code: "VERIFY_ALTERNATE_INCOME", title: "사업자 소득유형 확인", description: "대체 소득증빙을 확인합니다.", rationale: "A104 반복 실패", conditions: [], evidence: [{ source_type: "MANUAL", source_id: "income-verification-a104" }] }] }));
  await page.goto("/agent");
  await page.getByLabel("Context Pass ID").fill(passId);
  await page.getByRole("button", { name: "Context 조회" }).click();
  await expect(page.getByText("사업자 소득유형 확인")).toBeVisible();
  await expect(page.getByText("소득인증 단계에서 A104 오류가 발생했습니다.")).toBeVisible();
});

test("admin dashboard renders aggregate KPIs", async ({ page }) => {
  await page.route("**/api/v1/analytics/journeys", (route) => route.fulfill({ json: { total_journeys: 42, completion_rate: 66.7, failure_rate: 12.5, support_conversion_rate: 8.3, average_journey_duration_ms: 1200, top_failure_step: "INCOME_VERIFICATION", top_error_code: "A104" } }));
  await page.route("**/api/v1/analytics/failures", (route) => route.fulfill({ json: [{ category: "step", key: "INCOME_VERIFICATION", count: 8 }, { category: "error_code", key: "A104", count: 8 }] }));
  await page.route("**/api/v1/analytics/insights", (route) => route.fulfill({ json: { text: "A104 오류가 가장 많습니다.", based_on: [] } }));
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Journey 운영 현황" })).toBeVisible();
  await expect(page.getByText("42건")).toBeVisible();
  await expect(page.getByText("A104 오류가 가장 많습니다.")).toBeVisible();
});
