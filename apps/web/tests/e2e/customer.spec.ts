import { expect, test } from "@playwright/test";

const journeyId = "31000000-0000-4000-8000-000000000001";
const customerId = "21000000-0000-4000-8000-000000000001";

test("customer journey starts and restores after refresh", async ({ page }) => {
  let eventCount = 0;
  await page.route("**/api/v1/journeys", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        json: {
          id: journeyId, customer_id: customerId, product_type: "SOLE_PROPRIETOR_LOAN",
          status: "IN_PROGRESS", current_step: "PRODUCT_SELECTION", started_at: new Date().toISOString(),
          updated_at: new Date().toISOString(), events: [],
        },
        status: 201,
      });
    } else await route.continue();
  });
  await page.route(`**/api/v1/journeys/${journeyId}/events`, async (route) => {
    eventCount += 1;
    const event = route.request().postDataJSON();
    await route.fulfill({
      json: {
        event: { ...event, created_at: new Date().toISOString() },
        journey_status: "IN_PROGRESS", current_step: "PRODUCT_SELECTION", idempotent_replay: false,
      },
    });
  });
  await page.route(`**/api/v1/journeys/${journeyId}`, async (route) => {
    await route.fulfill({
      json: {
        id: journeyId, customer_id: customerId, product_type: "SOLE_PROPRIETOR_LOAN",
        status: "IN_PROGRESS", current_step: "PRODUCT_SELECTION", started_at: new Date().toISOString(),
        updated_at: new Date().toISOString(), events: [],
      },
    });
  });

  await page.goto("/customer");
  await expect(page.getByRole("heading", { name: "개인사업자 대출" })).toBeVisible();
  await page.getByRole("button", { name: "대출 신청 시작하기" }).click();
  await expect(page.getByText("개인사업자 신용대출 신청을 시작했습니다.")).toBeVisible();
  expect(eventCount).toBe(1);

  await page.reload();
  await expect(page.getByText("저장된 Journey를 복원했습니다.")).toBeVisible();
  await expect(page.getByText("상품 선택")).toBeVisible();
});
