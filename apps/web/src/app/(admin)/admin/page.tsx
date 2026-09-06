"use client";

import { useEffect, useState } from "react";

import {
  getAnalyticsFailures,
  getAnalyticsInsight,
  getAnalyticsSummary,
  type AnalyticsFailure,
  type AnalyticsInsight,
  type AnalyticsSummary,
} from "@/lib/api";

const stepLabels: Record<string, string> = {
  INCOME_VERIFICATION: "소득 인증", DOCUMENT_SUBMISSION: "서류 제출",
  IDENTITY_VERIFICATION: "본인 인증", LIMIT_CHECK: "한도 조회",
};

export default function AdminPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [failures, setFailures] = useState<AnalyticsFailure[]>([]);
  const [insight, setInsight] = useState<AnalyticsInsight | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getAnalyticsSummary(), getAnalyticsFailures(), getAnalyticsInsight()])
      .then(([nextSummary, nextFailures, nextInsight]) => {
        setSummary(nextSummary); setFailures(nextFailures); setInsight(nextInsight);
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "분석 데이터를 불러오지 못했습니다."));
  }, []);

  return (
    <main className="analytics-shell">
      <div className="eyebrow">FINPASS AI · ADMIN ANALYTICS</div>
      <div className="analytics-header"><div><h1>Journey 운영 현황</h1><p>고객의 금융업무 병목과 채널 전환을 한눈에 확인합니다.</p></div><span className="secure-badge">● 방금 업데이트</span></div>
      {error && <p className="error-message">{error}</p>}
      {!summary ? <section className="analytics-empty">분석 지표를 불러오는 중입니다...</section> : <>
        <section className="kpi-grid">{[["전체 Journey", summary.total_journeys.toLocaleString(), "건"], ["완료율", `${summary.completion_rate}%`, ""], ["실패율", `${summary.failure_rate}%`, ""], ["상담 전환율", `${summary.support_conversion_rate}%`, ""]].map(([label, value, suffix]) => <article className="kpi-card" key={label}><p>{label}</p><strong>{value}<small>{suffix}</small></strong></article>)}</section>
        <section className="analytics-columns"><article className="analytics-panel"><div className="panel-title"><div><span className="section-kicker">FAILURE DISTRIBUTION</span><h2>주요 실패 구간</h2></div><span className="status-pill warning">주의 필요</span></div><div className="bar-list">{failures.filter((item) => item.category === "step").slice(0, 5).map((item, index) => <div className="bar-item" key={item.key}><div><span>{stepLabels[item.key] ?? item.key}</span><strong>{item.count}건</strong></div><div className="bar-track"><span style={{ width: `${Math.max(8, item.count / Math.max(...failures.map((failure) => failure.count)) * 100)}%` }} /></div><small>#{index + 1}</small></div>)}{!failures.length && <p className="muted">아직 실패 데이터가 없습니다.</p>}</div></article><article className="analytics-panel"><div className="panel-title"><div><span className="section-kicker">AI INSIGHT</span><h2>운영 인사이트</h2></div><span className="status-pill">집계 근거</span></div><div className="insight-box">✦ <p>{insight?.text ?? "분석 중입니다."}</p></div><div className="mini-stat"><span>최다 오류 코드</span><strong>{summary.top_error_code ?? "-"}</strong></div><div className="mini-stat"><span>평균 이벤트 소요시간</span><strong>{summary.average_journey_duration_ms.toLocaleString()}ms</strong></div></article></section>
        <section className="analytics-panel error-table"><div className="panel-title"><div><span className="section-kicker">ERROR CODE</span><h2>오류 코드별 발생 현황</h2></div></div><div className="table-list">{failures.filter((item) => item.category === "error_code").map((item) => <div key={item.key}><span className="error-code-badge">{item.key}</span><span>소득 인증 실패</span><strong>{item.count}건</strong></div>)}{!failures.some((item) => item.category === "error_code") && <p className="muted">오류 코드 데이터가 없습니다.</p>}</div></section>
      </>}
    </main>
  );
}
