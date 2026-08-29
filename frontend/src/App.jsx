import { useEffect, useState } from "react";
import { getStatus, getChunks, runQuery, uploadPdf, reingest, deleteSource, clearAllSources } from "./api";
import PipelineTracker from "./components/PipelineTracker";
import IngestionPanel from "./components/IngestionPanel";
import QueryPanel from "./components/QueryPanel";

export default function App() {
  const [status, setStatus] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [queryLoading, setQueryLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [resetKey, setResetKey] = useState(0);
  const [step, setStep] = useState(4); // ingested-and-stored by default once data exists

  async function refresh() {
    try {
      const [s, c] = await Promise.all([getStatus(), getChunks()]);
      setStatus(s);
      setChunks(c.chunks);
      setError("");
      setStep(s.total_chunks > 0 ? 4 : 1);
    } catch {
      setError("Backend unreachable — is uvicorn running on :8000?");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleUpload(file) {
    setUploading(true);
    setError("");
    setNotice("");
    setStep(2);
    try {
      const res = await uploadPdf(file);
      const ing = res?.ingested;
      if (ing?.skipped === "duplicate") {
        // HTTP 200 with 0 chunks: the backend deduped it. Without this the
        // upload looks like it silently did nothing.
        setNotice(
          `"${ing.source}" holds the same content as "${ing.duplicate_of}" — already ingested, so it was skipped.`
        );
      } else if (ing) {
        setNotice(
          `Ingested "${ing.source}" — ${ing.chunks} chunk${ing.chunks === 1 ? "" : "s"} from ${ing.pages} section${ing.pages === 1 ? "" : "s"}.`
        );
      }
      setStep(4);
      await refresh();
    } catch (err) {
      setError(err.message || "Upload/ingest failed — check backend logs.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(name) {
    setError("");
    setNotice("");
    try {
      const res = await deleteSource(name);
      setResult(null);   // stale: it may cite chunks that no longer exist
      setNotice(`Removed "${name}" — ${res?.total_chunks ?? 0} chunks remain.`);
      await refresh();
    } catch (err) {
      setError(err.message || "Delete failed — check backend logs.");
    }
  }

  async function handleReset() {
    // Full reset: the ingested documents go too, so the app returns to the
    // state it had before anything was uploaded. That is destructive and not
    // recoverable — a deleted document has to be uploaded again — so it is
    // confirmed first rather than firing on a single click.
    const count = status?.total_chunks ?? 0;
    if (count > 0) {
      const names = Object.keys(status?.sources ?? {});
      const list = names.length ? "\n\n" + names.join("\n") : "";
      const plural = names.length === 1 ? "" : "s";
      const ok = window.confirm(
        `Reset will permanently delete ${names.length} document${plural} and all ${count} chunks.${list}` +
          "\n\nThis cannot be undone. Continue?"
      );
      if (!ok) return;
    }

    setError("");
    setNotice("");
    try {
      if (count > 0) await clearAllSources();
      setResult(null);
      // The question box and prompt toggle are QueryPanel's own state, so
      // bumping its key remounts it — clearing App state alone would leave the
      // previous question sitting in the input.
      setResetKey((k) => k + 1);
      setStep(1);
      await refresh();
      if (count > 0) setNotice("Reset — all documents removed. Ingest a document to start again.");
    } catch (err) {
      setError(err.message || "Reset failed — check backend logs.");
    }
  }

  async function handleQuery(question) {
    setQueryLoading(true);
    setError("");
    setStep(5);
    try {
      const res = await runQuery(question);
      setResult(res);
      setStep(6);
    } catch {
      setError("Query failed — check backend logs.");
    } finally {
      setQueryLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-800 px-6 py-4">
        <div className="flex items-center gap-3">
          <span className="flex h-8 w-8 items-center justify-center rounded bg-orange-500 text-neutral-950 font-bold">
            R
          </span>
          <div>
            <h1 className="text-base font-semibold leading-tight">RAG Explorer</h1>
            <p className="text-xs text-neutral-500">
              Doc (PDF/TXT/MD/Excel) &rarr; chunk &rarr; Nomic embed &rarr; ChromaDB &rarr; retrieve top-4 &rarr; Groq answer
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Badge label="ChromaDB" />
          <Badge label="nomic-embed-text" />
          <Badge label={status?.llm_model ?? "groq"} />
        </div>
      </header>

      <PipelineTracker activeStep={step} busy={uploading || queryLoading} />

      {error && (
        <p className="px-6 text-xs text-red-400 -mt-2 pb-2">{error}</p>
      )}

      {notice && !error && (
        <p className="px-6 text-xs text-emerald-400 -mt-2 pb-2">{notice}</p>
      )}

      <main className="grid grid-cols-1 lg:grid-cols-2 gap-6 px-6 pb-8">
        <IngestionPanel
          status={status}
          chunks={chunks}
          onUpload={handleUpload}
          onReset={handleReset}
          onDelete={handleDelete}
          uploading={uploading}
        />
        <QueryPanel
          key={resetKey}
          onSubmit={handleQuery}
          loading={queryLoading}
          result={result}
          error={null}
        />
      </main>
    </div>
  );
}

function Badge({ label }) {
  return (
    <span className="flex items-center gap-1.5 rounded-full border border-neutral-700 bg-neutral-900 px-3 py-1 text-xs text-neutral-300">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
      {label}
    </span>
  );
}
