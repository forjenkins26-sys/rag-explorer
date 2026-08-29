// The pipeline is two phases, not one run of six. Steps 1-4 happen once per
// document, at upload. Steps 5-6 happen again on every question asked. Laying
// them out as one flat row hides that; two labelled rows make it obvious which
// half is running and which half is already settled.
const PHASES = [
  {
    key: "ingest",
    label: "Ingest",
    note: "once per document",
    steps: [
      { n: 1, label: "Document", sub: "PDF · TXT · MD · Excel" },
      { n: 2, label: "Chunk", sub: "split on word boundaries" },
      { n: 3, label: "Embed", sub: "Nomic vectors" },
      { n: 4, label: "Store", sub: "ChromaDB" },
    ],
  },
  {
    key: "query",
    label: "Query",
    note: "every question",
    steps: [
      { n: 5, label: "Retrieve", sub: "top-k by cosine" },
      { n: 6, label: "Answer", sub: "Groq LLM" },
    ],
  },
];

export default function PipelineTracker({ activeStep, busy = false }) {
  return (
    <div className="flex flex-col gap-2 px-6 py-4">
      {PHASES.map((phase) => (
        <div key={phase.key} className="flex items-center gap-3">
          <div className="w-24 shrink-0">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
              {phase.label}
            </p>
            <p className="text-[10px] text-neutral-600">{phase.note}</p>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto">
            {phase.steps.map((step) => {
              const n = step.n;
              // The furthest step reached only pulses while work is actually
              // running; at rest it reads "done", so a settled pipeline never
              // looks like it is still mid-flight.
              const state =
                activeStep > n
                  ? "done"
                  : activeStep === n
                  ? busy
                    ? "active"
                    : "done"
                  : "idle";
              return (
                <div key={step.label} className="flex items-center gap-2 shrink-0">
                  <div
                    className={[
                      "flex items-center gap-2 rounded-lg border px-3 py-2 transition-colors",
                      state === "active"
                        ? "border-emerald-500/60 bg-emerald-500/10 animate-pulse"
                        : state === "done"
                        ? "border-emerald-800 bg-emerald-950/40"
                        : "border-neutral-800 bg-neutral-900/40",
                    ].join(" ")}
                  >
                    <span
                      className={[
                        "flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold shrink-0",
                        state === "idle"
                          ? "bg-neutral-800 text-neutral-500"
                          : "bg-emerald-500 text-neutral-950",
                      ].join(" ")}
                    >
                      {n}
                    </span>
                    <div className="text-left leading-tight">
                      <p className="text-sm font-medium text-neutral-100">{step.label}</p>
                      <p className="text-[11px] text-neutral-500">{step.sub}</p>
                    </div>
                  </div>
                  {step.n < 6 && step.n !== 4 && (
                    <span className="text-neutral-700">&rarr;</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
