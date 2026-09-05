/**
 * Bootstrap types for Phase 0. From Phase 1, this file is generated from the
 * FastAPI OpenAPI document; applications must not hand-edit generated output.
 */
export type HealthResponse = {
  status: "ok";
  environment: string;
};

export const JOURNEY_STATUSES = [
  "IN_PROGRESS",
  "ASSISTANCE_RECOMMENDED",
  "SUPPORT_REQUESTED",
  "IN_CONSULTATION",
  "ACTION_REQUIRED",
  "RESUMED",
  "COMPLETED",
] as const;

export type JourneyStatus = (typeof JOURNEY_STATUSES)[number];
