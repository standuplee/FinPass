import type { HealthResponse } from "@finpass/contracts";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getApiHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!response.ok) throw new Error(`API health check failed: ${response.status}`);
  return response.json() as Promise<HealthResponse>;
}
