import { useRef } from "react";

export default function IngestionPanel({ status, chunks, onUpload, onReset, onDelete, uploading }) {
  const fileRef = useRef(null);

  function handlePick() {
    fileRef.current?.click();
  }

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    e.target.value = "";
  }

  const sources = status ? Object.entries(status.sources) : [];

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-neutral-200">1 · Ingestion</h2>
        <div className="flex gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.txt,.md,.xlsx,.xls"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            onClick={handlePick}
            disabled={uploading}
            className="rounded bg-orange-500 px-3 py-1.5 text-xs font-semibold text-neutral-950 hover:bg-orange-400 disabled:opacity-50"
          >
            {uploading ? "Ingesting…" : "Ingest Document"}
          </button>
          <button
            onClick={onReset}
            title="Start over: permanently delete every ingested document and clear the question, answer and retrieved chunks. Asks for confirmation first."
            className="rounded border border-neutral-700 px-3 py-1.5 text-xs font-semibold text-neutral-300 hover:bg-neutral-800"
          >
            Reset
          </button>
        </div>
      </div>

      <p className="text-xs text-neutral-500 font-mono break-all">
        Source folder: {status?.pdf_folder}
      </p>
      <p className="text-xs text-neutral-600">
        Supported: PDF, TXT, Markdown, Excel (.xlsx/.xls)
      </p>

      {sources.length > 0 && (
        <ul className="flex flex-col gap-1">
          {sources.map(([name]) => (
            <li key={name} className="text-xs text-neutral-400 flex items-center gap-2 group">
              <span className="text-emerald-500">▣</span>
              <span className="flex-1 break-all">{name}</span>
              <button
                onClick={() => onDelete?.(name)}
                title={`Remove ${name}`}
                className="shrink-0 rounded border border-neutral-800 px-1.5 text-[11px] text-neutral-600 hover:border-red-600 hover:text-red-400 focus:border-red-600 focus:text-red-400 transition"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* "Stored" used to repeat the chunk count. These five say something
          different each: how much text came in, how it was cut, and what came
          out — which is the part a viewer is here to understand. */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <StatTile
          value={(status?.total_chars ?? 0).toLocaleString()}
          label="Characters"
        />
        <StatTile
          value={sources.reduce((sum, [, v]) => sum + v.pages, 0)}
          label="Pages"
        />
        <StatTile value={status?.total_chunks ?? 0} label="Chunks" />
        <StatTile value={status?.chunk_size ?? 0} label="Chunk size" />
        <StatTile value={status?.chunk_overlap ?? 0} label="Overlap" />
      </div>

      {status?.sample_embedding?.length > 0 && (
        <div>
          <p className="text-xs text-neutral-500 mb-1">
            Sample embedding (first {status.sample_embedding.length} of{" "}
            {status.embedding_dims})
          </p>
          <p className="font-mono text-xs text-emerald-400 break-all bg-neutral-900/60 rounded p-2 border border-neutral-800">
            [{status.sample_embedding.join(", ")}, ...]
          </p>
        </div>
      )}

      <div>
        <p className="text-xs text-neutral-500 mb-2">Chunk preview:</p>
        <div className="flex flex-col gap-2 max-h-80 overflow-y-auto pr-1">
          {chunks.length === 0 && (
            <p className="text-xs text-neutral-600">
              No chunks yet — ingest a PDF to see previews.
            </p>
          )}
          {chunks.map((c) => (
            <div
              key={`${c.source}-${c.index}`}
              className="rounded border border-neutral-800 bg-neutral-900/50 p-2"
            >
              <p className="text-xs font-semibold text-orange-400 mb-1">
                chunk {c.index} · {c.chars} chars
              </p>
              <p className="text-xs text-neutral-400 line-clamp-3">{c.content}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function StatTile({ value, label }) {
  return (
    <div className="rounded border border-neutral-800 bg-neutral-900/50 py-2 text-center">
      <p className="text-lg font-semibold text-neutral-100">{value}</p>
      <p className="text-[10px] uppercase tracking-wide text-neutral-500">{label}</p>
    </div>
  );
}
