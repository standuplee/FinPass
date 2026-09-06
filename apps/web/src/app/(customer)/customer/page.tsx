"use client";

import { useMemo, useState } from "react";

import {
  appendJourneyEvent,
  createJourney,
  type Journey,
  type JourneyStep,
} from "@/lib/api";

const steps: { id: JourneyStep; label: string }[] = [
  { id: "PRODUCT_SELECTION", label: "상품 선택" },
  { id: "BUSINESS_INFORMATION", label: "사업자 정보" },
  { id: "IDENTITY_VERIFICATION", label: "본인 인증" },
  { id: "LIMIT_CHECK", label: "한도 조회" },
  { id: "INCOME_VERIFICATION", label: "소득 인증" },
  { id: "DOCUMENT_SUBMISSION", label: "서류 제출" },
  { id: "APPLICATION_COMPLETION", label: "신청 완료" },
];

const eventForStep: Record<string, { event_type: string; status: "SUCCEEDED" }> = {
  PRODUCT_SELECTION: { event_type: "PRODUCT_VIEWED", status: "SUCCEEDED" },
  BUSINESS_INFORMATION: { event_type: "BUSINESS_INFORMATION_COMPLETED", status: "SUCCEEDED" },
  IDENTITY_VERIFICATION: { event_type: "IDENTITY_VERIFICATION_COMPLETED", status: "SUCCEEDED" },
  LIMIT_CHECK: { event_type: "LIMIT_CHECK_COMPLETED", status: "SUCCEEDED" },
  DOCUMENT_SUBMISSION: { event_type: "DOCUMENT_UPLOAD_COMPLETED", status: "SUCCEEDED" },
  APPLICATION_COMPLETION: { event_type: "JOURNEY_COMPLETED", status: "SUCCEEDED" },
};

export default function CustomerPage() {
  const [journey, setJourney] = useState<Journey | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [notice, setNotice] = useState("신청을 시작하면 진행 상황이 안전하게 저장됩니다.");
  const sessionId = useMemo(() => crypto.randomUUID(), []);

  const currentIndex = Math.max(0, steps.findIndex((step) => step.id === journey?.current_step));
  const currentStep = steps[currentIndex];
  const canStart = journey === null;
  const isFailure = journey?.status === "ASSISTANCE_RECOMMENDED";

  async function start() {
    setLoading(true);
    setError(null);
    try {
      const created = await createJourney({ customer_type: "SOLE_PROPRIETOR" });
      setJourney(created);
      await writeEvent(created, "JOURNEY_STARTED", "PRODUCT_SELECTION", "STARTED");
      setNotice("개인사업자 신용대출 신청을 시작했습니다.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "신청을 시작하지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function writeEvent(
    target: Journey,
    eventType: string,
    step: JourneyStep,
    status: "STARTED" | "SUCCEEDED" | "FAILED" | "REQUESTED",
    errorCode?: string,
  ) {
    const nextRetry = errorCode ? retryCount + 1 : retryCount;
    const result = await appendJourneyEvent(target.id, {
      event_id: crypto.randomUUID(),
      customer_id: target.customer_id,
      journey_id: target.id,
      session_id: sessionId,
      channel: "CUSTOMER_APP",
      event_type: eventType,
      product_type: "SOLE_PROPRIETOR_LOAN",
      journey_step: step,
      status,
      error_code: errorCode,
      retry_count: nextRetry,
      occurred_at: new Date().toISOString(),
      attributes: {},
    });
    setRetryCount(nextRetry);
    setJourney((previous) => previous ? { ...previous, status: result.journey_status, current_step: result.current_step, updated_at: new Date().toISOString(), events: [...previous.events, result.event] } : previous);
    return result;
  }

  async function advance() {
    if (!journey || !currentStep || loading) return;
    setLoading(true);
    setError(null);
    try {
      if (currentStep.id === "INCOME_VERIFICATION") {
        const next = retryCount + 1;
        await writeEvent(journey, "INCOME_VERIFICATION_FAILED", currentStep.id, "FAILED", "A104");
        setNotice(next >= 3 ? "인증에 반복 실패했습니다. 상담 연결을 권장합니다." : `인증에 실패했습니다 (A104). ${3 - next}회 더 실패하면 상담 연결을 안내합니다.`);
      } else {
        const event = eventForStep[currentStep.id];
        const result = await writeEvent(journey, event.event_type, currentStep.id, event.status);
        const nextStep = steps.find((step) => step.id === result.current_step);
        setNotice(nextStep ? `${nextStep.label} 단계로 이동했습니다.` : "신청이 완료되었습니다.");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "이벤트를 저장하지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function requestSupport() {
    if (!journey || loading) return;
    setLoading(true);
    try {
      const result = await writeEvent(journey, "SUPPORT_REQUESTED", "SUPPORT", "REQUESTED");
      setNotice(result.journey_status === "SUPPORT_REQUESTED" ? "상담 연결을 요청했습니다. 다음 단계에서 Context 공유 동의를 진행합니다." : "상담 연결 요청을 저장했습니다.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "상담 요청을 저장하지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="customer-shell">
      <div className="eyebrow">FINPASS AI · CUSTOMER APP</div>
      <div className="customer-header"><div><h1>개인사업자 대출</h1><p>중단되어도, 다음 채널에서 이어서 진행할 수 있어요.</p></div><span className="secure-badge">🔒 안전하게 저장됨</span></div>
      <section className="journey-card">
        <div className="card-heading"><div><p className="section-kicker">신청 진행률</p><h2>{journey ? currentStep?.label : "신청 준비"}</h2></div><span className={`status-pill ${isFailure ? "warning" : ""}`}>{journey?.status ?? "시작 전"}</span></div>
        <div className="progress-track">{steps.map((step, index) => <div className={`progress-step ${journey && index <= currentIndex ? "active" : ""} ${journey && index === currentIndex ? "current" : ""}`} key={step.id}><span>{index + 1}</span><small>{step.label}</small></div>)}</div>
        <div className="notice"><span>i</span><p>{notice}</p></div>
        {error && <p className="error-message">{error}</p>}
        {canStart ? <button className="primary-button" disabled={loading} onClick={start}>{loading ? "준비 중..." : "대출 신청 시작하기"}</button> : <div className="action-row"><button className="primary-button" disabled={loading || journey.status === "SUPPORT_REQUESTED" || journey.status === "COMPLETED"} onClick={advance}>{loading ? "저장 중..." : currentStep?.id === "INCOME_VERIFICATION" ? "소득 인증 다시 시도" : currentStep?.id === "APPLICATION_COMPLETION" ? "신청 완료하기" : "다음 단계로"}</button>{isFailure && <button className="secondary-button" disabled={loading} onClick={requestSupport}>상담 연결하기</button>}</div>}
      </section>
      {journey && <section className="event-card"><div className="card-heading"><div><p className="section-kicker">나의 Journey</p><h2>진행 기록</h2></div><span className="event-count">{journey.events.length}개 이벤트</span></div><div className="event-list">{journey.events.slice().reverse().map((event) => <div className="event-row" key={event.event_id}><span className={`event-dot ${event.status === "FAILED" ? "failed" : ""}`} /><div><strong>{event.event_type.replaceAll("_", " ")}</strong><small>{event.journey_step} · {new Date(event.occurred_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}</small></div>{event.error_code && <code>{event.error_code}</code>}</div>)}</div></section>}
    </main>
  );
}
