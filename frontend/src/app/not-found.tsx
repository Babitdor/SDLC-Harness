import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-dvh items-center bg-base-950 px-8">
      <div className="max-w-md">
        <span className="label-mono text-danger/80 block mb-3">
          404 / NO ROUTE
        </span>
        <h1 className="text-[28px] leading-[1.1] tracking-[-0.02em] text-base-100 font-semibold mb-3">
          That page isn&rsquo;t part of the harness.
        </h1>
        <p className="text-[14px] text-base-400 leading-relaxed mb-8">
          The orchestrator runs on a single view. Conversations, artifacts and
          the inspector all live there — nothing is routed off it.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 border border-base-600 px-4 py-2 text-[13px] font-mono text-base-300 transition-colors hover:border-blue-400/60 hover:bg-blue-400/10 hover:text-blue-300"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          Back to the orchestrator
        </Link>
      </div>
    </main>
  );
}
