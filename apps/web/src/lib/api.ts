import type { HealthResponse } from "@finpass/contracts";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getApiHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!response.ok) throw new Error(`API health check failed: ${response.status}`);
  return response.json() as Promise<HealthResponse>;
}

export type JourneyStep =
  | "PRODUCT_SELECTION"
  | "BUSINESS_INFORMATION"
  | "IDENTITY_VERIFICATION"
  | "LIMIT_CHECK"
  | "INCOME_VERIFICATION"
  | "DOCUMENT_SUBMISSION"
  | "APPLICATION_COMPLETION"
  | "SUPPORT";

export type JourneyStatus =
  | "IN_PROGRESS"
  | "ASSISTANCE_RECOMMENDED"
  | "SUPPORT_REQUESTED"
  | "COMPLETED";

export type JourneyEvent = {
  event_id: string;
  customer_id: string;
  journey_id: string;
  session_id: string;
  channel: "CUSTOMER_APP";
  event_type: string;
  product_type: "SOLE_PROPRIETOR_LOAN";
  journey_step: JourneyStep;
  status: "STARTED" | "SUCCEEDED" | "FAILED" | "REQUESTED" | "COMPLETED";
  error_code?: string;
  retry_count: number;
  occurred_at: string;
  duration_ms?: number;
  attributes: Record<string, unknown>;
  created_at?: string;
};

export type Journey = {
  id: string;
  customer_id: string;
  product_type: "SOLE_PROPRIETOR_LOAN";
  status: JourneyStatus;
  current_step: JourneyStep;
  started_at: string;
  updated_at: string;
  events: JourneyEvent[];
};

type EventWriteResult = {
  event: JourneyEvent;
  journey_status: JourneyStatus;
  current_step: JourneyStep;
  idempotent_replay: boolean;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function createJourney(customerSegment: Record<string, unknown> = {}) {
  return request<Journey>("/api/v1/journeys", {
    method: "POST",
    body: JSON.stringify({ product_type: "SOLE_PROPRIETOR_LOAN", customer_segment: customerSegment }),
  });
}

export function appendJourneyEvent(journeyId: string, event: JourneyEvent, idempotencyKey?: string) {
  return request<EventWriteResult>(`/api/v1/journeys/${journeyId}/events`, {
    method: "POST",
    headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
    body: JSON.stringify(event),
  });
}

export function getJourney(journeyId: string) {
  return request<Journey>(`/api/v1/journeys/${journeyId}`);
}

export type Consent = {
  id: string;
  journey_id: string;
  customer_id: string;
  scope: string[];
  status: "ACTIVE" | "REVOKED";
  expires_at: string;
  created_at: string;
  revoked_at: string | null;
};

export function createConsent(journeyId: string, scope: string[] = ["JOURNEY_CONTEXT", "FAILURE_EVIDENCE"]) {
  return request<Consent>(`/api/v1/journeys/${journeyId}/consents`, {
    method: "POST",
    body: JSON.stringify({ scope, ttl_minutes: 30 }),
  });
}

export function createContextPass(journeyId: string, consentId: string) {
  return request<ContextPass>(`/api/v1/journeys/${journeyId}/context-pass?consent_id=${consentId}`, {
    method: "POST",
  });
}

export type ContextPass = {
  id: string;
  journey_id: string;
  consent_id: string;
  payload: {
    current_product: string;
    current_step: JourneyStep;
    completed_steps: string[];
    failure_step: string | null;
    error_codes: string[];
    retry_count: number;
    customer_intent: string;
  };
  created_at: string;
  expires_at: string;
};

export type Consultation = {
  id: string;
  journey_id: string;
  context_pass_id: string;
  status: "OPEN" | "COMPLETED";
  outcome: string | null;
  next_step: JourneyStep | null;
  notes: string | null;
  created_at: string;
  completed_at: string | null;
};

export function getContextPass(passId: string) {
  return request<ContextPass>(`/api/v1/journeys/context-pass/${passId}`);
}

export function createConsultation(passId: string) {
  return request<Consultation>(`/api/v1/journeys/context-pass/${passId}/consultations`, {
    method: "POST",
  });
}

export function completeConsultation(
  consultationId: string,
  body: { outcome: string; next_step: JourneyStep; notes?: string },
) {
  return request<Consultation>(`/api/v1/journeys/consultations/${consultationId}/complete`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
