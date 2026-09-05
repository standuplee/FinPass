import Link from "next/link";

const surfaces = [
  ["Customer App", "/customer", "개인사업자 대출 Journey"],
  ["Agent Copilot", "/agent", "Context와 상담 지원"],
  ["Admin Analytics", "/admin", "Journey 운영 지표"],
] as const;

export default function Home() {
  return (
    <main>
      <p>Financial Journey Intelligence</p>
      <h1>FinPass AI</h1>
      <div className="cards">
        {surfaces.map(([title, href, description]) => (
          <article className="card" key={href}>
            <h2>{title}</h2>
            <p>{description}</p>
            <Link href={href}>화면 열기</Link>
          </article>
        ))}
      </div>
    </main>
  );
}
