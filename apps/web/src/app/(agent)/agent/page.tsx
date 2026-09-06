"use client";

import { useState } from "react";

import {
  completeConsultation,
  createConsultation,
  getContextPass,
  getJourney,
  analyzeJourney,
  type Consultation,
  type ContextPass,
  type Journey,
  type ContextInterpretation,
} from "@/lib/api";

const labels: Record<string, string> = {
  PRODUCT_SELECTION: "상품 선택", BUSINESS_INFORMATION: "사업자 정보",
  IDENTITY_VERIFICATION: "본인 인증", LIMIT_CHECK: "한도 조회",
  INCOME_VERIFICATION: "소득 인증", DOCUMENT_SUBMISSION: "서류 제출",
  APPLICATION_COMPLETION: "신청 완료", SUPPORT: "상담 지원",
};

export default function AgentPage() {
  const [passId, setPassId] = useState("");
  const [context, setContext] = useState<ContextPass | null>(null);
  const [journey, setJourney] = useState<Journey | null>(null);
  const [consultation, setConsultation] = useState<Consultation | null>(null);
  const [interpretation, setInterpretation] = useState<ContextInterpretation | null>(null);
  const [outcome, setOutcome] = useState("대체 소득증빙 방법 안내");
  const [notes, setNotes] = useState("사업자 소득금액증명원 제출을 안내했습니다.");
  const [message, setMessage] = useState("Context Pass ID를 입력하면 고객의 업무 맥락을 불러옵니다.");
  const [loading, setLoading] = useState(false);

  async function loadContext() {
    if (!passId.trim()) return;
    setLoading(true);
    try {
      const loaded = await getContextPass(passId.trim());
      const loadedJourney = await getJourney(loaded.journey_id);
      const interpreted = await analyzeJourney(loaded.journey_id);
      setContext(loaded);
      setJourney(loadedJourney);
      setInterpretation(interpreted);
      setMessage("동의된 최소 Context를 확인했습니다. 상담을 시작하세요.");
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Context를 불러오지 못했습니다.");
    } finally { setLoading(false); }
  }

  async function startConsultation() {
    if (!context) return;
    setLoading(true);
    try {
      setConsultation(await createConsultation(context.id));
      setMessage("상담이 시작되었습니다. 안내 결과를 기록해 주세요.");
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "상담을 시작하지 못했습니다."); }
    finally { setLoading(false); }
  }

  async function finishConsultation() {
    if (!consultation) return;
    setLoading(true);
    try {
      const completed = await completeConsultation(consultation.id, {
        outcome, next_step: "DOCUMENT_SUBMISSION", notes,
      });
      setConsultation(completed);
      setMessage("상담 결과가 저장되었습니다. 고객은 서류 제출 단계부터 재개할 수 있습니다.");
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "상담 결과를 저장하지 못했습니다."); }
    finally { setLoading(false); }
  }

  const failures = journey?.events.filter((event) => event.status === "FAILED") ?? [];
  return (
    <main className="agent-shell">
      <div className="eyebrow">FINPASS AI · AGENT COPILOT</div>
      <div className="agent-header"><div><h1>고객 Journey Context</h1><p>고객이 설명을 반복하지 않아도, 지금 필요한 업무부터 이어갑니다.</p></div><span className="secure-badge">● 실시간 상담 지원</span></div>
      <section className="agent-search"><label htmlFor="pass-id">Context Pass ID</label><div className="search-row"><input id="pass-id" value={passId} onChange={(event) => setPassId(event.target.value)} placeholder="예: 4f3c..." /><button className="primary-button" disabled={loading || !passId.trim()} onClick={loadContext}>{loading ? "불러오는 중..." : "Context 조회"}</button></div><p>{message}</p></section>
      {context && <>
        <section className="copilot-grid">
          <article className="agent-panel context-summary"><div className="panel-title"><span className="section-kicker">AI CONTEXT SUMMARY</span><span className="status-pill">Event 근거 {interpretation?.evidence.length ?? 0}건</span></div><h2>{interpretation?.summary ?? "Journey Context를 해석하는 중입니다."}</h2><p>현재 단계: {labels[context.payload.current_step] ?? context.payload.current_step} · 오류: {context.payload.error_codes.join(", ") || "없음"} · 재시도: {context.payload.retry_count}회</p><div className="intent-tag">고객 목적 · {interpretation?.customer_intent === "SOLE_PROPRIETOR_LOAN_APPLICATION" ? "대출 신청" : interpretation?.customer_intent}</div></article>
          <article className="agent-panel"><div className="panel-title"><span className="section-kicker">FAILURE EVIDENCE</span><span className="warning-text">확인 필요</span></div>{failures.length ? <div className="evidence-list">{failures.map((event) => <div className="evidence-row" key={event.event_id}><strong>{event.error_code}</strong><span>{labels[event.journey_step] ?? event.journey_step} · 재시도 {event.retry_count}회</span></div>)}</div> : <p className="muted">실패 이벤트가 없습니다.</p>}</article>
        </section>
        <section className="agent-panel timeline-panel"><div className="panel-title"><div><span className="section-kicker">CUSTOMER JOURNEY TIMELINE</span><h2>업무 진행 기록</h2></div><span className="status-pill warning">{journey?.status}</span></div><div className="timeline">{journey?.events.map((event) => <div className="timeline-item" key={event.event_id}><span className={`event-dot ${event.status === "FAILED" ? "failed" : ""}`} /><div><strong>{event.event_type.replaceAll("_", " ")}</strong><small>{labels[event.journey_step] ?? event.journey_step} · {new Date(event.occurred_at).toLocaleString("ko-KR")}</small></div>{event.error_code && <code>{event.error_code}</code>}</div>)}</div></section>
        <section className="agent-panel action-panel"><div className="panel-title"><div><span className="section-kicker">NEXT BEST ACTION</span><h2>상담원이 확인할 항목</h2></div><span className="status-pill">AI 추천</span></div><div className="action-card"><span>01</span><div><strong>대체 소득증빙 절차 안내</strong><p>사업자 소득금액증명원 또는 부가세 과세표준증명원 제출 가능 여부를 확인하세요.</p></div></div><div className="action-card"><span>02</span><div><strong>모바일 서류 제출 링크 제공</strong><p>상담 완료 후 고객은 서류 제출 단계에서 Journey를 재개합니다.</p></div></div>{!consultation ? <button className="primary-button" disabled={loading} onClick={startConsultation}>상담 시작하기</button> : consultation.status === "OPEN" ? <div className="consult-form"><label htmlFor="outcome">상담 결과</label><input id="outcome" value={outcome} onChange={(event) => setOutcome(event.target.value)} /><label htmlFor="notes">상담 메모</label><textarea id="notes" value={notes} onChange={(event) => setNotes(event.target.value)} /><button className="primary-button" disabled={loading} onClick={finishConsultation}>상담 완료 · 고객에게 전달</button></div> : <div className="success-box">✓ 상담 완료 · 고객은 {labels[consultation.next_step ?? "DOCUMENT_SUBMISSION"]}부터 재개합니다.</div>}</section>
      </>}
    </main>
  );
}
