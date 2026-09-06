import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const baseURL = "http://127.0.0.1:3000";
const executablePath = process.env.PLAYWRIGHT_EXECUTABLE_PATH;
const outputDir = "../../docs/assets/proposal-captures";

await mkdir(outputDir, { recursive: true });
const browser = await chromium.launch({ headless: true, executablePath });

const agent = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
const journeyId = "31000000-0000-4000-8000-000000000001";
const passId = "51000000-0000-4000-8000-000000000001";
await agent.route(`**/api/v1/journeys/context-pass/${passId}`, (route) => route.fulfill({ json: {
  id: passId, journey_id: journeyId, consent_id: "consent-1",
  payload: { current_step: "INCOME_VERIFICATION", completed_steps: ["PRODUCT_SELECTION", "IDENTITY_VERIFICATION", "LIMIT_CHECK"], failure_step: "INCOME_VERIFICATION", error_codes: ["A104"], retry_count: 3, customer_intent: "SOURCE_OF_FUNDS_VERIFICATION" },
  created_at: new Date().toISOString(), expires_at: new Date(Date.now() + 1800000).toISOString(),
} }));
await agent.route(`**/api/v1/journeys/${journeyId}`, (route) => route.fulfill({ json: {
  id: journeyId, customer_id: "customer-1", product_type: "SOLE_PROPRIETOR_LOAN", status: "ASSISTANCE_RECOMMENDED", current_step: "INCOME_VERIFICATION", started_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  events: [{ event_id: "event-1", event_type: "INCOME_VERIFICATION_FAILED", journey_step: "INCOME_VERIFICATION", status: "FAILED", error_code: "A104", retry_count: 3, occurred_at: new Date().toISOString() }],
} }));
await agent.route(`**/api/v1/journeys/${journeyId}/analyze`, (route) => route.fulfill({ json: {
  journey_id: journeyId, current_step: "INCOME_VERIFICATION", completed_steps: ["PRODUCT_SELECTION", "IDENTITY_VERIFICATION", "LIMIT_CHECK"], failure_step: "INCOME_VERIFICATION", error_codes: ["A104"], retry_count: 3, customer_intent: "SOURCE_OF_FUNDS_VERIFICATION", intent_confidence: 0.96, intent_source: "RULE", summary: "고객은 개인사업자 신용대출 한도조회를 완료했으며 소득인증 단계에서 A104 오류가 3회 발생한 후 상담 연결을 요청했습니다.", evidence: [{ source_type: "JOURNEY_EVENT", source_id: "event-1" }],
} }));
await agent.route(`**/api/v1/journeys/${journeyId}/actions`, (route) => route.fulfill({ json: [{ action_code: "VERIFY_ALTERNATE_INCOME", title: "사업자 소득유형 확인", description: "대체 소득증빙 절차를 안내합니다.", rationale: "A104 반복 실패", conditions: [], evidence: [{ source_type: "MANUAL", source_id: "income-verification-a104" }] }] }));
await agent.goto(`${baseURL}/agent`);
await agent.getByLabel("Context Pass ID").fill(passId);
await agent.getByRole("button", { name: "Context 조회" }).click();
await agent.screenshot({ path: `${outputDir}/04-agent-copilot.png`, fullPage: true });

const admin = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
await admin.route("**/api/v1/analytics/journeys", (route) => route.fulfill({ json: { total_journeys: 1248, completion_rate: 72.4, failure_rate: 18.7, support_conversion_rate: 11.3, average_journey_duration_ms: 252000, top_failure_step: "INCOME_VERIFICATION", top_error_code: "A104" } }));
await admin.route("**/api/v1/analytics/failures", (route) => route.fulfill({ json: [{ category: "step", key: "INCOME_VERIFICATION", count: 233 }, { category: "error_code", key: "A104", count: 187 }] }));
await admin.route("**/api/v1/analytics/insights", (route) => route.fulfill({ json: { text: "최근 소득인증 단계의 A104 오류가 전체 실패의 37%를 차지하며 상담 전환율을 높이고 있습니다.", based_on: [] } }));
await admin.goto(`${baseURL}/admin`);
await admin.screenshot({ path: `${outputDir}/05-admin-analytics.png`, fullPage: true });

const customer = await browser.newPage({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 2 });
const customerJourneyId = "31000000-0000-4000-8000-000000000002";
const customerId = "21000000-0000-4000-8000-000000000002";
const customerEvents = [];
await customer.route("**/api/v1/journeys", (route) => route.fulfill({ status: 201, json: {
  id: customerJourneyId, customer_id: customerId, product_type: "SOLE_PROPRIETOR_LOAN", status: "IN_PROGRESS", current_step: "PRODUCT_SELECTION", started_at: new Date().toISOString(), updated_at: new Date().toISOString(), events: [],
} }));
await customer.route(`**/api/v1/journeys/${customerJourneyId}/events`, async (route) => {
  const event = route.request().postDataJSON();
  customerEvents.push(event);
  const next = { JOURNEY_STARTED: "PRODUCT_SELECTION", PRODUCT_VIEWED: "BUSINESS_INFORMATION", BUSINESS_INFORMATION_COMPLETED: "IDENTITY_VERIFICATION", IDENTITY_VERIFICATION_FAILED: "IDENTITY_VERIFICATION", IDENTITY_VERIFICATION_COMPLETED: "LIMIT_CHECK", LIMIT_CHECK_FAILED: "LIMIT_CHECK", LIMIT_CHECK_COMPLETED: "INCOME_VERIFICATION" }[event.event_type] ?? "INCOME_VERIFICATION";
  await route.fulfill({ json: { event: { ...event, created_at: new Date().toISOString() }, journey_status: "IN_PROGRESS", current_step: next, idempotent_replay: false } });
});
await customer.route(`**/api/v1/journeys/${customerJourneyId}`, (route) => route.fulfill({ json: { id: customerJourneyId, customer_id: customerId, product_type: "SOLE_PROPRIETOR_LOAN", status: "IN_PROGRESS", current_step: "PRODUCT_SELECTION", started_at: new Date().toISOString(), updated_at: new Date().toISOString(), events: customerEvents } }));
await customer.route(`**/api/v1/journeys/${customerJourneyId}/chat`, (route) => route.fulfill({ json: { answer: "현재 본인 인증 단계에서 AUTH_TIMEOUT 오류가 확인되었습니다. 잠시 후 다시 시도하고, 문제가 반복되면 가까운 영업점 방문이나 콜센터 연결을 이용해 주세요.", current_step: "IDENTITY_VERIFICATION", error_codes: ["AUTH_TIMEOUT"], retry_count: 1, suggested_channels: ["CALL_CENTER", "BRANCH"], context_used: ["CURRENT_STEP", "FAILURE_EVIDENCE", "RETRY_COUNT", "CUSTOMER_INTENT"] } }));
await customer.goto(`${baseURL}/customer`);
await customer.getByRole("button", { name: "대출 신청 시작하기" }).click();
await customer.getByRole("button", { name: "다음 단계로" }).click();
await customer.getByRole("button", { name: "다음 단계로" }).click();
await customer.getByRole("button", { name: "다음 단계로" }).click();
await customer.screenshot({ path: `${outputDir}/01-identity-error.png`, fullPage: true });
await customer.getByRole("button", { name: "확인" }).click();
await customer.getByRole("button", { name: "다음 단계로" }).click();
await customer.getByRole("button", { name: "다음 단계로" }).click();
await customer.screenshot({ path: `${outputDir}/02-limit-error.png`, fullPage: true });
await customer.getByRole("button", { name: "확인" }).click();
await customer.getByRole("button", { name: "FinPass AI 상담 챗봇" }).click();
await customer.getByPlaceholder("오류 해결 방법을 질문해 보세요").fill("왜 인증이 되지 않나요?");
await customer.getByRole("button", { name: "질문" }).click();
await customer.screenshot({ path: `${outputDir}/03-context-chat-handoff.png`, fullPage: true });

await browser.close();
console.log(`Saved proposal captures to ${outputDir}`);
