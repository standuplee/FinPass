"use client";

import { useEffect, useMemo, useState } from "react";

import {
  appendJourneyEvent,
  createConsent,
  createContextPass,
  getJourney,
  createJourney,
  type Journey,
  type JourneyStep,
  type ContextPass,
  askJourneyChat,
  type JourneyChatResponse,
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
  const [contextPass, setContextPass] = useState<ContextPass | null>(null);
  const [consentChecked, setConsentChecked] = useState(false);
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatAnswer, setChatAnswer] = useState<JourneyChatResponse | null>(null);
  const sessionId = useMemo(() => crypto.randomUUID(), []);

  useEffect(() => {
    const savedJourneyId = window.localStorage.getItem("finpass_journey_id");
    if (!savedJourneyId) return;
    getJourney(savedJourneyId)
      .then((savedJourney) => {
        setJourney(savedJourney);
        const failures = savedJourney.events.filter((event) => event.status === "FAILED");
        setRetryCount(Math.max(...failures.map((event) => event.retry_count), 0));
        setNotice("저장된 Journey를 복원했습니다. 중단된 단계부터 계속 진행하세요.");
      })
      .catch(() => window.localStorage.removeItem("finpass_journey_id"));
  }, []);

  const currentIndex = Math.max(0, steps.findIndex((step) => step.id === journey?.current_step));
  const currentStep = steps[currentIndex];
  const canStart = journey === null;
  const isFailure = journey?.status === "ASSISTANCE_RECOMMENDED";

  async function start() {
    setLoading(true);
    setError(null);
    try {
      const created = await createJourney({ customer_type: "SOLE_PROPRIETOR" });
      window.localStorage.setItem("finpass_journey_id", created.id);
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

  async function askChat() {
    if (!journey || !chatQuestion.trim() || loading) return;
    setLoading(true);
    try {
      setChatAnswer(await askJourneyChat(journey.id, chatQuestion.trim()));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "챗봇 답변을 불러오지 못했습니다.");
    } finally { setLoading(false); }
  }

  async function consentAndCreatePass() {
    if (!journey || !consentChecked || loading) return;
    setLoading(true);
    setError(null);
    try {
      const consent = await createConsent(journey.id);
      const pass = await createContextPass(journey.id, consent.id);
      window.localStorage.setItem("finpass_context_pass_id", pass.id);
      setContextPass(pass);
      setNotice("상담원에게 필요한 최소 정보만 공유했습니다. 아래 Pass ID를 상담원에게 전달하세요.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Context 공유 동의를 처리하지 못했습니다.");
    } finally { setLoading(false); }
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
      {isFailure && <section className="chat-card"><div className="section-kicker">FINPASS AI 상담 챗봇</div><h2>지금 상황을 바탕으로 안내받기</h2><p>현재 대출 단계와 반복 오류를 반영해 답변합니다. 처음부터 다시 설명하지 않아도 됩니다.</p><div className="chat-input"><input value={chatQuestion} onChange={(event) => setChatQuestion(event.target.value)} placeholder="예: 소득 인증 오류를 어떻게 해결하나요?" onKeyDown={(event) => { if (event.key === "Enter") void askChat(); }} /><button className="secondary-button" disabled={loading || !chatQuestion.trim()} onClick={askChat}>질문하기</button></div>{chatAnswer && <div className="chat-answer"><strong>현재 Journey 기반 답변</strong><p>{chatAnswer.answer}</p><small>반영된 Context: 현재 단계 · 실패 근거 · 재시도 횟수 · 고객 목적</small><div className="channel-actions"><button className="primary-button" onClick={requestSupport}>콜센터 연결</button><button className="secondary-button" onClick={requestSupport}>영업점 방문 안내</button></div></div>}</section>}
      {journey?.status === "SUPPORT_REQUESTED" && <section className="consent-card"><div className="section-kicker">CONTEXT SHARE CONSENT</div><h2>상담원에게 진행 상황을 공유할까요?</h2><p>전체 금융 로그가 아닌, 현재 대출 신청에 필요한 정보만 30분 동안 공유합니다.</p><label className="consent-check"><input type="checkbox" checked={consentChecked} onChange={(event) => setConsentChecked(event.target.checked)} /> <span>Journey 단계, 실패 오류, 재시도 횟수, 고객 목적을 공유하는 데 동의합니다.</span></label>{contextPass ? <div className="pass-result"><small>상담원에게 전달할 Context Pass ID</small><code>{contextPass.id}</code><span>만료: {new Date(contextPass.expires_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}</span></div> : <button className="primary-button" disabled={!consentChecked || loading} onClick={consentAndCreatePass}>{loading ? "발급 중..." : "동의하고 Context Pass 발급"}</button>}</section>}
    </main>
  );
}
