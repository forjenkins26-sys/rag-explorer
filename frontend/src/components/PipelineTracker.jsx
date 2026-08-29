// Six steps, one row — but the pipeline is really two phases, and the divider
// after step 4 is where that shows. Steps 1-4 run once per document, at upload.
// Steps 5-6 run again on every question. A flat row of six hides that; splitting
// it into two rows breaks the sequence. A single row with a rule between the
// phases keeps the flow readable and still says which half is which.
const STEPS = [
  { n: 1, label: "Document", sub: "PDF · TXT · MD · Excel" },
  { n: 2, label: "Chunk", sub: "split on word boundaries" },
  { n: 3, label: "Embed", sub: "Nomic vectors" },
  { n: 4, label: "Store", sub: "ChromaDB" },
  { n: 5, label: "Retrieve", sub: "top-k by cosine" },
  { n: 6, label: "Answer", sub: "Groq LLM" },
];

const PHASE_BREAK = 4; // last ingestion step

export default function PipelineTracker({ activeStep, busy = false }) {
  return (
    <div className="px-6 py-4">
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {STEPS.map((step) => {
          // The furthest step reached only pulses while work is actually
          // running. At rest it reads "done", so a settled pipeline never looks
          // like it is still mid-flight.
          const state =
            activeStep > step.n
              ? "done"
              : activeStep === step.n
              ? busy
                ? "active"
                : "done"
              : "idle";

          return (
            <div key={step.n} className="flex items-center gap-2 shrink-0">
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
                  {step.n}
                </span>
                <div className="text-left leading-tight">
                  <p className="text-sm font-medium text-neutral-100">{step.label}</p>
                  <p className="text-[11px] text-neutral-500">{step.sub}</p>
                </div>
              </div>

              {step.n === PHASE_BREAK ? (
                <span
                  aria-hidden="true"
                  className="mx-1 h-10 w-px shrink-0 bg-neutral-700"
                />
              ) : step.n < STEPS.length ? (
                <span className="text-neutral-700">&rarr;</span>
              ) : null}
            </div>
          );
        })}
      </div>

      {/* The legend is what makes the divider mean something. Without it the
          rule reads as decoration rather than a phase boundary. */}
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-neutral-500">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-500/60 animate-pulse" />
          running
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-800" />
          done
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-neutral-700" />
          idle
        </span>
        <span className="text-neutral-600">
          Left of the divider runs once per document · right runs on every question
        </span>
      </div>
    </div>
  );
}
