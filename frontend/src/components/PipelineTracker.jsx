const STEPS = [
  { label: "PDF", sub: "load document" },
  { label: "Chunk", sub: "split text" },
  { label: "Embed", sub: "Nomic vectors" },
  { label: "Store", sub: "ChromaDB" },
  { label: "Retrieve", sub: "top-k" },
  { label: "Answer", sub: "Groq LLM" },
];

export default function PipelineTracker({ activeStep }) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto px-6 py-4">
      {STEPS.map((step, i) => {
        const state =
          activeStep > i + 1 ? "done" : activeStep === i + 1 ? "active" : "idle";
        return (
          <div key={step.label} className="flex items-center gap-2 shrink-0">
            <div
              className={[
                "flex items-center gap-2 rounded-lg border px-3 py-2 transition-colors",
                state === "active"
                  ? "border-emerald-500/60 bg-emerald-500/10"
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
                {i + 1}
              </span>
              <div className="text-left leading-tight">
                <p className="text-sm font-medium text-neutral-100">{step.label}</p>
                <p className="text-[11px] text-neutral-500">{step.sub}</p>
              </div>
            </div>
            {i < STEPS.length - 1 && (
              <span className="text-neutral-700">&rarr;</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
