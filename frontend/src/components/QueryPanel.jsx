import { useState } from "react";

const EXAMPLES = [
  "What is the goal of this PRD?",
  "Who are the target users?",
  "What are the key features described?",
  "What are the success metrics?",
];

export default function QueryPanel({ onSubmit, loading, result, error }) {
  const [value, setValue] = useState("");
  const [showPrompt, setShowPrompt] = useState(false);

  function submit(question) {
    if (!question.trim() || loading) return;
    setValue(question);
    onSubmit(question.trim());
  }

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-neutral-200">2 · Ask the document</h2>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
        className="flex gap-2"
      >
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask a question about the ingested document…"
          className="flex-1 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-orange-500"
        />
        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="rounded bg-orange-500 px-4 py-2 text-sm font-semibold text-neutral-950 disabled:opacity-40 hover:bg-orange-400"
        >
          {loading ? "Asking…" : "Ask"}
        </button>
      </form>

      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((q) => (
          <button
            key={q}
            onClick={() => submit(q)}
            className="rounded-full border border-neutral-700 px-3 py-1 text-xs text-neutral-400 hover:border-orange-500 hover:text-orange-400"
          >
            {q}
          </button>
        ))}
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <div className="rounded border border-neutral-800 bg-neutral-900/50 p-3">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Answer
          </p>
          {result?.tokens != null && (
            <p className="text-[11px] text-neutral-500">
              {result.chunks?.length ? "groq" : ""} · {result.tokens} tok
            </p>
          )}
        </div>

        {loading && <p className="text-sm text-neutral-500">Generating…</p>}
        {!loading && !result && (
          <p className="text-sm text-neutral-600">Ask a question to see the answer.</p>
        )}
        {!loading && result && (
          <>
            <p className="text-sm text-neutral-100 leading-relaxed whitespace-pre-wrap border-l-2 border-orange-500 pl-3">
              {result.answer}
            </p>
            {result.prompt && (
              <div className="mt-3">
                <button
                  onClick={() => setShowPrompt((v) => !v)}
                  className="text-xs text-orange-400 hover:text-orange-300"
                >
                  {showPrompt ? "Hide" : "Show"} the augmented prompt sent to Groq
                </button>
                {showPrompt && (
                  <pre className="mt-2 max-h-64 overflow-y-auto rounded bg-neutral-950 p-2 text-[11px] text-neutral-400 whitespace-pre-wrap border border-neutral-800">
                    {result.prompt}
                  </pre>
                )}
              </div>
            )}
          </>
        )}
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500 mb-2">
          Retrieved context · top {result?.chunks?.length ?? 0}
        </p>
        <div className="flex flex-col gap-2 max-h-96 overflow-y-auto pr-1">
          {(result?.chunks ?? []).map((c) => (
            <div
              key={c.chunk_number}
              className="rounded border border-neutral-800 bg-neutral-900/50 p-3"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-orange-400">
                  #{c.chunk_number} {c.source} · chunk {c.chunk_number}
                </span>
                <span className="rounded-full bg-emerald-500/10 border border-emerald-700 px-2 py-0.5 text-[11px] text-emerald-400">
                  {Math.round(c.similarity * 100)}% match
                </span>
              </div>
              <p className="text-xs text-neutral-500 mb-1">page {c.page}</p>
              <p className="text-xs text-neutral-300 leading-relaxed">{c.content}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
